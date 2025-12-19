# CHIMERA Tracking Server Dockerfile
FROM node:18-alpine

# Install system dependencies for canvas
RUN apk add --no-cache \
    build-base \
    cairo-dev \
    jpeg-dev \
    giflib-dev \
    librsvg-dev \
    pango-dev \
    python3

# Create application directory
WORKDIR /app

# Copy package files
COPY chimera/tracking_server/package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy application code
COPY chimera/tracking_server/ ./

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S chimera -u 1001

# Change ownership
RUN chown -R chimera:nodejs /app
USER chimera

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8080/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Run the application
CMD ["npm", "start"]


