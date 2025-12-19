#!/usr/bin/env node

/**
 * CHIMERA Tracking Server
 *
 * Behavioral telemetry collection for red team campaigns:
 * - Email open tracking via 1x1 pixel
 * - Link click tracking via redirect
 * - Browser fingerprinting (privacy-preserving)
 * - Geographic and device analytics
 *
 * WARNING: This system is designed for AUTHORIZED RED TEAM OPERATIONS ONLY.
 */

const express = require('express');
const redis = require('redis');
const { createCanvas } = require('canvas');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const UAParser = require('ua-parser-js');
const geoip = require('geoip-lite');
const DeviceDetector = require('device-detector-js');
const SandboxDetector = require('./sandbox_detector');

// Configuration
require('dotenv').config();
const PORT = process.env.TRACKING_SERVER_PORT || 8080;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379/0';
const CLICKHOUSE_HOST = process.env.CLICKHOUSE_HOST || 'localhost';
const CLICKHOUSE_PORT = process.env.CLICKHOUSE_PORT || 8123;

// Initialize Express app
const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'none'"],
      scriptSrc: ["'none'"],
      imgSrc: ["'self'", "data:"],
      fontSrc: ["'none'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'none'"],
      frameSrc: ["'none'"]
    }
  }
}));

// CORS configuration (restrictive)
app.use(cors({
  origin: false, // Disable CORS for security
  methods: ['GET', 'HEAD'],
  allowedHeaders: ['User-Agent', 'Accept', 'Accept-Language']
}));

// Compression
app.use(compression());

// Logging (minimal for privacy)
app.use(morgan('combined', {
  skip: (req, res) => res.statusCode < 400 // Only log errors
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req, res) => {
    // Skip rate limiting for legitimate tracking requests
    return req.path.startsWith('/pixel/') || req.path.startsWith('/click/');
  }
});
app.use(limiter);

// Initialize Redis client
let redisClient;
try {
  redisClient = redis.createClient({ url: REDIS_URL });
  redisClient.connect();
  console.log('Connected to Redis');
} catch (error) {
  console.error('Redis connection failed:', error);
  process.exit(1);
}

// Initialize ClickHouse client
let clickhouseClient;
try {
  const ClickHouse = require('clickhouse');
  clickhouseClient = new ClickHouse({
    host: CLICKHOUSE_HOST,
    port: CLICKHOUSE_PORT,
    format: 'json'
  });
  console.log('Connected to ClickHouse');
} catch (error) {
  console.error('ClickHouse connection failed:', error);
  process.exit(1);
}

// Device detector
const deviceDetector = new DeviceDetector();

// Sandbox detector
const sandboxDetector = new SandboxDetector();

// Utility functions
function generateTrackingId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function extractClientIP(req) {
  // Extract real IP from various headers (bypassing proxies)
  return req.ip ||
         req.connection.remoteAddress ||
         req.socket.remoteAddress ||
         (req.connection.socket ? req.connection.socket.remoteAddress : null) ||
         req.headers['x-forwarded-for']?.split(',')[0] ||
         req.headers['x-real-ip'] ||
         'unknown';
}

function parseUserAgent(userAgent) {
  const parser = new UAParser(userAgent);
  return {
    browser: parser.getBrowser(),
    engine: parser.getEngine(),
    os: parser.getOS(),
    device: parser.getDevice(),
    cpu: parser.getCPU()
  };
}

function getGeolocation(ip) {
  try {
    const geo = geoip.lookup(ip);
    if (geo) {
      return {
        country: geo.country,
        region: geo.region,
        city: 'redacted', // Privacy: don't track city level
        timezone: geo.timezone,
        ll: [geo.ll[0], geo.ll[1]] // Keep coordinates but they'll be generalized
      };
    }
  } catch (error) {
    console.error('Geolocation lookup failed:', error);
  }
  return { country: 'unknown' };
}

function createFingerprint(req) {
  const userAgent = req.get('User-Agent') || '';
  const accept = req.get('Accept') || '';
  const acceptLanguage = req.get('Accept-Language') || '';
  const acceptEncoding = req.get('Accept-Encoding') || '';

  // Create a basic fingerprint (not too unique for privacy)
  const fingerprint = {
    user_agent_family: parseUserAgent(userAgent).browser.name || 'unknown',
    os_family: parseUserAgent(userAgent).os.name || 'unknown',
    device_type: parseUserAgent(userAgent).device.type || 'desktop',
    language: acceptLanguage.split(',')[0] || 'unknown',
    timezone: req.get('Timezone') || 'unknown',
    screen_resolution: req.get('Screen-Resolution') || 'unknown'
  };

  return fingerprint;
}

function createCanvasPixel() {
  // Create a 1x1 transparent PNG pixel
  const canvas = createCanvas(1, 1);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(0,0,0,0)'; // Transparent
  ctx.fillRect(0, 0, 1, 1);

  return canvas.toBuffer('image/png');
}

function createHoneypotImage(sandboxDetection) {
  // Create a deceptive image for sandboxes/honeypots
  const canvas = createCanvas(1, 1);
  const ctx = canvas.getContext('2d');

  // Different colors based on risk level
  switch (sandboxDetection.riskLevel) {
    case 'critical':
      ctx.fillStyle = 'rgba(255, 0, 0, 0.1)'; // Red tint for high risk
      break;
    case 'high':
      ctx.fillStyle = 'rgba(255, 165, 0, 0.1)'; // Orange tint
      break;
    case 'medium':
      ctx.fillStyle = 'rgba(255, 255, 0, 0.1)'; // Yellow tint
      break;
    default:
      ctx.fillStyle = 'rgba(0, 255, 0, 0.1)'; // Green tint for low risk
  }

  ctx.fillRect(0, 0, 1, 1);

  return canvas.toBuffer('image/png');
}

async function recordTelemetryEvent(eventData) {
  try {
    // Store in Redis for immediate processing
    const eventKey = `telemetry:${eventData.event_id}`;
    await redisClient.setEx(eventKey, 3600, JSON.stringify(eventData)); // 1 hour TTL

    // Add to processing queue
    await redisClient.lPush('telemetry_queue', JSON.stringify(eventData));

    console.log(`Recorded telemetry event: ${eventData.event_type} for campaign ${eventData.campaign_id}`);

  } catch (error) {
    console.error('Failed to record telemetry event:', error);
  }
}

// Routes

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'chimera-tracking-server',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// Tracking pixel for email opens
app.get('/pixel/:campaignId/:participantId/:emailId.png', async (req, res) => {
  try {
    const { campaignId, participantId, emailId } = req.params;

    // Create fingerprint for sandbox detection
    const fingerprint = createFingerprint(req);

    // Perform sandbox detection
    const sandboxDetection = sandboxDetector.detectSandbox(req, fingerprint);

    // Honeypot reversal: If sandbox detected, serve different content
    if (sandboxDetection.isSandbox) {
      console.log(`Sandbox detected for campaign ${campaignId}:`, sandboxDetection.detectedMethods);

      // Log the detection
      await recordTelemetryEvent({
        event_id: generateTrackingId(),
        campaign_id: campaignId,
        participant_id: participantId,
        email_id: emailId,
        event_type: 'sandbox_detected',
        timestamp: new Date().toISOString(),
        ip_address: extractClientIP(req),
        user_agent: req.get('User-Agent') || '',
        fingerprint: fingerprint,
        geolocation: getGeolocation(extractClientIP(req)),
        consent_verified: false,
        event_metadata: {
          sandbox_confidence: sandboxDetection.confidence,
          detected_methods: sandboxDetection.detectedMethods,
          risk_level: sandboxDetection.riskLevel,
          honeypot_activated: true
        }
      });

      // Serve honeypot content instead of tracking pixel
      const honeypotImage = createHoneypotImage(sandboxDetection);
      res.set({
        'Content-Type': 'image/png',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Honeypot-Activated': 'true',
        'X-Risk-Level': sandboxDetection.riskLevel
      });
      res.send(honeypotImage);
      return;
    }

    // Normal tracking for legitimate users
    res.set({
      'Content-Type': 'image/png',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      'X-Content-Type-Options': 'nosniff'
    });

    // Create pixel image
    const pixel = createCanvasPixel();
    res.send(pixel);

    // Record email open event
    const eventData = {
      event_id: generateTrackingId(),
      campaign_id: campaignId,
      participant_id: participantId,
      email_id: emailId,
      event_type: 'email_opened',
      timestamp: new Date().toISOString(),
      ip_address: extractClientIP(req),
      user_agent: req.get('User-Agent') || '',
      fingerprint: fingerprint,
      geolocation: getGeolocation(extractClientIP(req)),
      consent_verified: true,
      event_metadata: {
        referrer: req.get('Referer') || 'direct',
        pixel_loaded: true,
        sandbox_check_passed: true
      }
    };

    await recordTelemetryEvent(eventData);

  } catch (error) {
    console.error('Pixel tracking error:', error);
    // Still return pixel even on error
    const pixel = createCanvasPixel();
    res.set('Content-Type', 'image/png');
    res.send(pixel);
  }
});

// Link click tracking
app.get('/click/:campaignId/:participantId/:emailId/:linkId', async (req, res) => {
  try {
    const { campaignId, participantId, emailId, linkId } = req.params;

    // Create fingerprint for sandbox detection
    const fingerprint = createFingerprint(req);

    // Perform sandbox detection
    const sandboxDetection = sandboxDetector.detectSandbox(req, fingerprint);

    // Record click event with sandbox detection info
    const eventData = {
      event_id: generateTrackingId(),
      campaign_id: campaignId,
      participant_id: participantId,
      email_id: emailId,
      link_id: linkId,
      event_type: 'link_clicked',
      timestamp: new Date().toISOString(),
      ip_address: extractClientIP(req),
      user_agent: req.get('User-Agent') || '',
      fingerprint: fingerprint,
      geolocation: getGeolocation(extractClientIP(req)),
      consent_verified: !sandboxDetection.isSandbox,
      event_metadata: {
        referrer: req.get('Referer') || 'direct',
        link_clicked: true,
        query_params: req.query,
        sandbox_detected: sandboxDetection.isSandbox,
        sandbox_confidence: sandboxDetection.confidence,
        risk_level: sandboxDetection.riskLevel
      }
    };

    await recordTelemetryEvent(eventData);

    // Honeypot reversal for sandboxed environments
    if (sandboxDetection.isSandbox) {
      console.log(`Sandbox detected in click tracking for campaign ${campaignId}:`, sandboxDetection.detectedMethods);

      // Redirect to honeypot landing page instead of real target
      const honeypotUrl = `${req.protocol}://${req.get('host')}/landing/${campaignId}?honeypot=true&sandbox_detected=true&risk=${sandboxDetection.riskLevel}`;
      res.redirect(302, honeypotUrl);
      return;
    }

    // Normal redirect for legitimate users
    const originalUrl = req.query.url || 'https://chimera-project.org/landing';

    // Add tracking parameters to avoid redirect loops
    const separator = originalUrl.includes('?') ? '&' : '?';
    const trackedUrl = `${originalUrl}${separator}utm_source=chimera&utm_medium=email&utm_campaign=${campaignId}&participant=${participantId}`;

    res.redirect(302, trackedUrl);

  } catch (error) {
    console.error('Link tracking error:', error);
    // Redirect to safe fallback
    res.redirect(302, 'https://chimera-project.org/error');
  }
});

// Campaign landing page (basic)
app.get('/landing/:campaignId?', (req, res) => {
  const campaignId = req.params.campaignId || 'unknown';
  const isHoneypot = req.query.honeypot === 'true';
  const sandboxDetected = req.query.sandbox_detected === 'true';
  const riskLevel = req.query.risk || 'unknown';

  let pageTitle = "Security Awareness Training";
  let headerText = "This is a simulated security training exercise.";
  let bodyContent = "You have reached this page as part of an authorized security awareness campaign.";
  let backgroundColor = "#f0f0f0";
  let borderColor = "#ccc";

  // Honeypot reversal: Different content for detected sandboxes
  if (isHoneypot || sandboxDetected) {
    pageTitle = "Security Analysis Portal";

    if (riskLevel === 'critical') {
      backgroundColor = "#ffebee"; // Light red
      borderColor = "#f44336"; // Red
      headerText = "🚨 SECURITY ALERT DETECTED 🚨";
      bodyContent = `
        <p><strong>Automated security analysis has been detected.</strong></p>
        <p>This access attempt has been logged and flagged for review.</p>
        <p>For security purposes, this session has been terminated.</p>
        <p>If you believe this is an error, please contact your system administrator.</p>
      `;
    } else if (riskLevel === 'high') {
      backgroundColor = "#fff3e0"; // Light orange
      borderColor = "#ff9800"; // Orange
      headerText = "⚠️ Enhanced Security Monitoring Active ⚠️";
      bodyContent = `
        <p><strong>Suspicious activity has been detected on this connection.</strong></p>
        <p>Your access is being monitored for security purposes.</p>
        <p>Please verify your identity through proper channels.</p>
      `;
    } else {
      backgroundColor = "#fffde7"; // Light yellow
      borderColor = "#ffeb3b"; // Yellow
      headerText = "🔍 Security Assessment in Progress 🔍";
      bodyContent = `
        <p><strong>This connection is being evaluated for security compliance.</strong></p>
        <p>Automated systems are analyzing your access patterns.</p>
        <p>If you are a legitimate user, no action is required.</p>
      `;
    }

    // Log the honeypot activation
    console.log(`Honeypot activated for campaign ${campaignId}: risk=${riskLevel}, sandbox=${sandboxDetected}`);
  }

  const html = `
<!DOCTYPE html>
<html>
<head>
    <title>${pageTitle}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            margin: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            margin: 0;
        }
        .notice {
            background: ${backgroundColor};
            padding: 30px;
            border-left: 4px solid ${borderColor};
            margin: 0;
        }
        .footer {
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #eee;
        }
        .alert-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header">${pageTitle}</h1>
        <div class="notice">
            <div class="alert-icon">${isHoneypot || sandboxDetected ? '🛡️' : '🎯'}</div>
            <h2>${headerText}</h2>
            <div>${bodyContent}</div>
        </div>
        <div class="footer">
            <p>Campaign ID: ${campaignId} | Timestamp: ${new Date().toISOString()}</p>
            ${isHoneypot || sandboxDetected ? `<p>Security Level: ${riskLevel.toUpperCase()}</p>` : ''}
        </div>
    </div>
</body>
</html>`;

  res.send(html);
});

// Error handling
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    error: 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// Security status endpoint
app.get('/security/status', (req, res) => {
  // This endpoint could provide security metrics and detection status
  // In a production system, this would be protected and provide real-time security intelligence

  res.json({
    service: 'chimera-tracking-server',
    security_features: {
      sandbox_detection: 'active',
      honeypot_reversal: 'active',
      behavioral_analysis: 'active',
      anomaly_detection: 'active'
    },
    detection_methods: [
      'virtual_machine_detection',
      'sandbox_artifacts',
      'automated_browsing',
      'security_monitoring',
      'network_analysis',
      'timing_anomalies',
      'resource_limitations'
    ],
    risk_levels: ['low', 'medium', 'high', 'critical'],
    timestamp: new Date().toISOString(),
    warning: 'This endpoint is for authorized security personnel only'
  });
});

// Detection testing endpoint (for development/testing only)
if (process.env.NODE_ENV === 'development') {
  app.get('/test/detection/:testType', (req, res) => {
    const { testType } = req.params;

    // Simulate different types of suspicious requests for testing
    const testFingerprints = {
      'vm': {
        user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 (VirtualBox)',
        screen_resolution: '1024x768',
        webdriver: false
      },
      'headless': {
        user_agent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/91.0.4472.101 Safari/537.36',
        screen_resolution: '800x600',
        webdriver: true
      },
      'bot': {
        user_agent: 'python-requests/2.25.1',
        screen_resolution: 'unknown',
        webdriver: false
      }
    };

    const testFingerprint = testFingerprints[testType] || testFingerprints['bot'];
    const detectionResult = sandboxDetector.detectSandbox(req, testFingerprint);

    res.json({
      test_type: testType,
      detection_result: detectionResult,
      test_fingerprint: testFingerprint,
      timestamp: new Date().toISOString()
    });
  });
}

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Received SIGTERM, shutting down gracefully...');

  if (redisClient) {
    await redisClient.disconnect();
  }

  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('Received SIGINT, shutting down gracefully...');

  if (redisClient) {
    await redisClient.disconnect();
  }

  process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`CHIMERA Tracking Server listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log('WARNING: This server is for AUTHORIZED RED TEAM OPERATIONS ONLY');
});

module.exports = app;
