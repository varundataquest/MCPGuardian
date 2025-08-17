# 🚀 MCP Registry Harvester - Deployment Guide

## Quick Deploy Options

### **Option 1: Railway (Recommended - 5 minutes)**

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Deploy:**
   ```bash
   railway init
   railway up
   ```

4. **Get your URL:**
   ```bash
   railway domain
   ```

### **Option 2: Render (Alternative)**

1. **Connect your GitHub repo to Render**
2. **Create a new Web Service**
3. **Use these settings:**
   - **Build Command:** `pip install poetry && poetry install`
   - **Start Command:** `poetry run mcp-harvest devserver --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3.11

### **Option 3: Docker Deployment**

1. **Build the image:**
   ```bash
   docker build -t mcp-harvest .
   ```

2. **Run locally:**
   ```bash
   docker run -p 8000:8000 mcp-harvest
   ```

3. **Deploy to cloud:**
   - **Google Cloud Run:**
     ```bash
     gcloud run deploy mcp-harvest --image mcp-harvest --platform managed
     ```
   - **AWS ECS/Fargate**
   - **Azure Container Instances**

### **Option 4: Heroku**

1. **Install Heroku CLI**
2. **Deploy:**
   ```bash
   heroku create your-app-name
   git push heroku main
   heroku open
   ```

## Environment Variables

Set these environment variables in your deployment platform:

```bash
# Optional: Set to control crawling behavior
CRAWL_INCLUDE=docker,mcp-get
CRAWL_EXCLUDE=

# Optional: Set for production
ENVIRONMENT=production
```

## Data Persistence

The application stores data in the `data/` directory. For production:

1. **Use persistent storage** (Railway/Render provide this automatically)
2. **Set up regular backups** of the `data/` directory
3. **Consider using a database** for larger datasets

## Performance Considerations

- **Memory:** Application uses ~500MB-1GB RAM
- **CPU:** Moderate usage during crawling
- **Storage:** Data directory grows with discovered servers
- **Network:** Crawls external sources during startup

## Monitoring

The application includes health checks at `/` endpoint.

## Troubleshooting

### Common Issues:

1. **Port binding errors:**
   - Ensure using `0.0.0.0` instead of `127.0.0.1`
   - Use `$PORT` environment variable

2. **Poetry installation:**
   - Some platforms need explicit Poetry installation
   - Use `pip install poetry && poetry install`

3. **Data directory:**
   - Ensure `data/` directory exists and is writable
   - Use persistent storage in production

### Logs:

Check application logs for:
- Crawling progress
- Integration status
- Server startup messages

## Security Considerations

1. **Rate limiting:** Consider adding rate limiting for public deployments
2. **Authentication:** Add auth if needed for sensitive data
3. **CORS:** Configure CORS for web frontend access
4. **HTTPS:** Use HTTPS in production

## Scaling

For high traffic:
1. **Use multiple instances** behind a load balancer
2. **Implement caching** for search results
3. **Use a CDN** for static assets
4. **Consider database** for better performance

## Support

- Check the application logs for errors
- Verify all dependencies are installed
- Ensure proper file permissions
- Test locally before deploying 