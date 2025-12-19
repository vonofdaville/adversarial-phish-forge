/**
 * Sandbox Detection Module
 *
 * Detects automated analysis environments and security monitoring systems.
 * Implements evasion techniques to avoid detection while maintaining ethics.
 */

const crypto = require('crypto');

class SandboxDetector {
    constructor() {
        this.detectionMethods = [
            this.detectVirtualMachine.bind(this),
            this.detectSandboxArtifacts.bind(this),
            this.detectAutomatedBrowsing.bind(this),
            this.detectSecurityMonitoring.bind(this),
            this.detectNetworkAnalysis.bind(this),
            this.detectTimingAnomalies.bind(this),
            this.detectResourceLimitations.bind(this)
        ];

        this.evasionTechniques = [
            this.applyUserAgentRotation.bind(this),
            this.addHumanLikeDelays.bind(this),
            this.simulateHumanBehavior.bind(this),
            this.randomizeRequestPatterns.bind(this),
            this.addNoiseToFingerprint.bind(this)
        ];
    }

    /**
     * Perform comprehensive sandbox detection
     * @param {Object} request - Express request object
     * @param {Object} fingerprint - Device fingerprint
     * @returns {Object} Detection results
     */
    detectSandbox(request, fingerprint) {
        const detectionResults = {
            isSandbox: false,
            confidence: 0.0,
            detectedMethods: [],
            riskLevel: 'low',
            evasionApplied: false,
            recommendations: []
        };

        // Run all detection methods
        for (const detectionMethod of this.detectionMethods) {
            const result = detectionMethod(request, fingerprint);
            if (result.detected) {
                detectionResults.isSandbox = true;
                detectionResults.confidence = Math.max(detectionResults.confidence, result.confidence);
                detectionResults.detectedMethods.push(result.method);
                detectionResults.riskLevel = this._calculateRiskLevel(detectionResults.confidence);
            }
        }

        // Apply evasion if sandbox detected
        if (detectionResults.isSandbox) {
            detectionResults.evasionApplied = this._applyEvasionTechniques(request, detectionResults);
            detectionResults.recommendations = this._generateRecommendations(detectionResults);
        }

        return detectionResults;
    }

    /**
     * Detect virtual machine environments
     */
    detectVirtualMachine(request, fingerprint) {
        const userAgent = request.get('User-Agent') || '';
        const method = 'virtual_machine_detection';

        let confidence = 0.0;
        let detected = false;

        // Check for known VM user agents
        const vmIndicators = [
            'virtualbox',
            'vmware',
            'qemu',
            'xen',
            'kvm',
            'hyper-v',
            'parallels'
        ];

        for (const indicator of vmIndicators) {
            if (userAgent.toLowerCase().includes(indicator)) {
                confidence += 0.8;
                detected = true;
            }
        }

        // Check for VM-specific screen resolutions
        const screenRes = fingerprint.screen_resolution;
        const suspiciousResolutions = ['1024x768', '800x600', '640x480'];
        if (suspiciousResolutions.includes(screenRes)) {
            confidence += 0.3;
        }

        // Check for headless browser indicators
        if (userAgent.includes('Headless') || userAgent.includes('PhantomJS')) {
            confidence += 0.9;
            detected = true;
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'VM or headless browser detected' : null
        };
    }

    /**
     * Detect sandbox artifacts
     */
    detectSandboxArtifacts(request, fingerprint) {
        const method = 'sandbox_artifacts';
        let confidence = 0.0;
        let detected = false;

        // Check for sandbox-specific file paths
        const suspiciousPaths = [
            'c:\\sandbox',
            'c:\\virus',
            'c:\\sample',
            '/sandbox',
            '/tmp/sandbox'
        ];

        const referrer = request.get('Referer') || '';
        for (const path of suspiciousPaths) {
            if (referrer.includes(path)) {
                confidence += 0.7;
                detected = true;
            }
        }

        // Check for sandbox process names in user agent
        const processIndicators = [
            'sandboxie',
            'cuckoo',
            'joebox',
            'threattrack',
            'anubis'
        ];

        const userAgent = request.get('User-Agent') || '';
        for (const indicator of processIndicators) {
            if (userAgent.toLowerCase().includes(indicator)) {
                confidence += 0.9;
                detected = true;
            }
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Sandbox artifacts detected in request' : null
        };
    }

    /**
     * Detect automated browsing patterns
     */
    detectAutomatedBrowsing(request, fingerprint) {
        const method = 'automated_browsing';
        let confidence = 0.0;
        let detected = false;

        // Check for missing human-like headers
        const requiredHeaders = ['Accept-Language', 'Accept-Encoding', 'Cache-Control'];
        for (const header of requiredHeaders) {
            if (!request.get(header)) {
                confidence += 0.2;
            }
        }

        // Check for suspicious timing patterns
        const timing = this._analyzeRequestTiming(request);
        if (timing.isSuspicious) {
            confidence += timing.confidence;
            detected = true;
        }

        // Check for bot-like user agent
        const userAgent = request.get('User-Agent') || '';
        const botIndicators = [
            'bot', 'crawler', 'spider', 'scraper',
            'python', 'java/', 'go-http-client'
        ];

        for (const indicator of botIndicators) {
            if (userAgent.toLowerCase().includes(indicator)) {
                confidence += 0.6;
                detected = true;
            }
        }

        // Check for webdriver property (Selenium)
        if (fingerprint.webdriver === true) {
            confidence += 0.95;
            detected = true;
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Automated browsing patterns detected' : null
        };
    }

    /**
     * Detect security monitoring systems
     */
    detectSecurityMonitoring(request, fingerprint) {
        const method = 'security_monitoring';
        let confidence = 0.0;
        let detected = false;

        // Check for security tool user agents
        const securityTools = [
            'wireshark', 'fiddler', 'burp', 'zap', 'charles',
            'mitmproxy', 'tcpdump', 'nessus', 'qualys'
        ];

        const userAgent = request.get('User-Agent') || '';
        for (const tool of securityTools) {
            if (userAgent.toLowerCase().includes(tool)) {
                confidence += 0.8;
                detected = true;
            }
        }

        // Check for honeypot-like IP ranges (example ranges)
        const ip = this._extractIP(request);
        const honeypotRanges = [
            '192.0.2.0/24',    // RFC 5737 test range
            '198.51.100.0/24', // RFC 5737 test range
            '203.0.113.0/24'   // RFC 5737 test range
        ];

        // Simple IP range check (in production, use proper IP range libraries)
        if (ip && ip.startsWith('192.0.2.')) {
            confidence += 0.7;
            detected = true;
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Security monitoring detected' : null
        };
    }

    /**
     * Detect network analysis tools
     */
    detectNetworkAnalysis(request, fingerprint) {
        const method = 'network_analysis';
        let confidence = 0.0;
        let detected = false;

        // Check for proxy headers
        const proxyHeaders = [
            'x-forwarded-for',
            'x-real-ip',
            'x-proxy-id',
            'via',
            'x-bluecoat-via'
        ];

        let proxyCount = 0;
        for (const header of proxyHeaders) {
            if (request.get(header)) {
                proxyCount++;
            }
        }

        if (proxyCount > 2) {
            confidence += 0.6;
            detected = true;
        }

        // Check for suspicious referrer patterns
        const referrer = request.get('Referer') || '';
        const suspiciousReferrers = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            'test.com',
            'example.com'
        ];

        for (const suspicious of suspiciousReferrers) {
            if (referrer.includes(suspicious)) {
                confidence += 0.4;
                detected = true;
            }
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Network analysis patterns detected' : null
        };
    }

    /**
     * Detect timing anomalies
     */
    detectTimingAnomalies(request, fingerprint) {
        const method = 'timing_anomalies';
        let confidence = 0.0;
        let detected = false;

        // Check for impossibly fast requests
        const timing = this._analyzeRequestTiming(request);
        if (timing.tooFast) {
            confidence += 0.8;
            detected = true;
        }

        // Check for perfect timing patterns (too regular)
        if (timing.tooRegular) {
            confidence += 0.5;
            detected = true;
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Suspicious timing patterns detected' : null
        };
    }

    /**
     * Detect resource limitations (common in sandboxes)
     */
    detectResourceLimitations(request, fingerprint) {
        const method = 'resource_limitations';
        let confidence = 0.0;
        let detected = false;

        // Check for limited screen resolution
        const screenRes = fingerprint.screen_resolution;
        if (screenRes === 'unknown' || screenRes === '0x0') {
            confidence += 0.4;
            detected = true;
        }

        // Check for missing browser features
        if (!fingerprint.language || fingerprint.language === 'unknown') {
            confidence += 0.2;
        }

        if (!fingerprint.timezone || fingerprint.timezone === 'unknown') {
            confidence += 0.2;
        }

        return {
            method,
            detected,
            confidence: Math.min(confidence, 1.0),
            details: detected ? 'Resource limitations detected' : null
        };
    }

    /**
     * Apply evasion techniques
     */
    _applyEvasionTechniques(request, detectionResults) {
        let evasionApplied = false;

        for (const technique of this.evasionTechniques) {
            try {
                const applied = technique(request, detectionResults);
                if (applied) {
                    evasionApplied = true;
                }
            } catch (error) {
                console.error('Evasion technique failed:', error);
            }
        }

        return evasionApplied;
    }

    /**
     * Apply user agent rotation
     */
    applyUserAgentRotation(request, detectionResults) {
        // This would modify the response based on detection
        // For now, just log the detection
        console.log('Applying user agent rotation evasion');
        return true;
    }

    /**
     * Add human-like delays
     */
    addHumanLikeDelays(request, detectionResults) {
        // This would introduce artificial delays
        console.log('Adding human-like delays');
        return true;
    }

    /**
     * Simulate human behavior
     */
    simulateHumanBehavior(request, detectionResults) {
        // This would modify response to appear more human
        console.log('Simulating human behavior patterns');
        return true;
    }

    /**
     * Randomize request patterns
     */
    randomizeRequestPatterns(request, detectionResults) {
        // This would randomize response patterns
        console.log('Randomizing request patterns');
        return true;
    }

    /**
     * Add noise to fingerprint
     */
    addNoiseToFingerprint(request, detectionResults) {
        // This would add noise to tracking data
        console.log('Adding noise to fingerprint');
        return true;
    }

    /**
     * Analyze request timing
     */
    _analyzeRequestTiming(request) {
        const now = Date.now();
        const startTime = request.startTime || now;

        const duration = now - startTime;
        const tooFast = duration < 10; // Less than 10ms
        const tooRegular = this._checkRegularTiming(duration);

        return {
            duration,
            tooFast,
            tooRegular,
            isSuspicious: tooFast || tooRegular,
            confidence: tooFast ? 0.8 : (tooRegular ? 0.5 : 0.0)
        };
    }

    /**
     * Check for regular timing patterns
     */
    _checkRegularTiming(duration) {
        // Check if timing is suspiciously regular (every 1000ms, etc.)
        const commonIntervals = [1000, 2000, 5000, 10000, 30000, 60000];
        for (const interval of commonIntervals) {
            if (Math.abs(duration % interval) < 50) {
                return true;
            }
        }
        return false;
    }

    /**
     * Extract IP address from request
     */
    _extractIP(request) {
        return request.ip ||
               request.connection.remoteAddress ||
               request.socket.remoteAddress ||
               request.connection.socket?.remoteAddress ||
               null;
    }

    /**
     * Calculate risk level from confidence
     */
    _calculateRiskLevel(confidence) {
        if (confidence >= 0.8) return 'critical';
        if (confidence >= 0.6) return 'high';
        if (confidence >= 0.4) return 'medium';
        return 'low';
    }

    /**
     * Generate recommendations based on detection
     */
    _generateRecommendations(detectionResults) {
        const recommendations = [];

        if (detectionResults.confidence >= 0.8) {
            recommendations.push('Immediate campaign termination recommended');
            recommendations.push('Security incident should be reported');
        } else if (detectionResults.confidence >= 0.6) {
            recommendations.push('Consider campaign modification');
            recommendations.push('Increase monitoring frequency');
        } else {
            recommendations.push('Continue monitoring');
            recommendations.push('Log for analysis');
        }

        if (detectionResults.detectedMethods.includes('automated_browsing')) {
            recommendations.push('Implement bot detection measures');
        }

        if (detectionResults.detectedMethods.includes('virtual_machine_detection')) {
            recommendations.push('Review VM-based testing procedures');
        }

        return recommendations;
    }
}

module.exports = SandboxDetector;

