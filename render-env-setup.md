# Render Environment Variables Setup

After deploying with render.yaml, set these environment variables in the Render dashboard:

## Backend API Service (mcpguardian-api)

### Required (Database)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_ANON_KEY=your_anon_key_here
```

### Required (API Configuration)  
```bash
API_BASE_URL=https://mcpguardian-api.onrender.com
NEXT_PUBLIC_API_BASE=https://mcpguardian-api.onrender.com
```

### Optional (AI Features)
```bash
GEMINI_API_KEY=your_gemini_key_here
GITHUB_TOKEN=your_github_token_here
```

## MCP Server Service (mcpguardian-mcp)

### Required (Database)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

### Optional (AI Features)
```bash
GEMINI_API_KEY=your_gemini_key_here  
GITHUB_TOKEN=your_github_token_here
```

## Frontend Service (mcpguardian-ui)

### Required
```bash
NEXT_PUBLIC_API_BASE=https://mcpguardian-api.onrender.com
NEXT_PUBLIC_ADMIN_ACCESS_TOKEN=your_secure_admin_token
```

## Service URLs After Deployment
- Frontend: https://mcpguardian-ui.onrender.com
- API: https://mcpguardian-api.onrender.com  
- MCP Server: https://mcpguardian-mcp.onrender.com/mcp

## Notes
- Replace `your-project` with your actual Supabase project URL
- Admin token is pre-configured as `prod-admin-token-secure-12345`
- All services will automatically use Render's assigned PORT environment variable
