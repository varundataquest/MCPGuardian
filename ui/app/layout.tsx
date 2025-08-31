import './globals.css'
import type { ReactNode } from 'react'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AgentAgentGo - MCPGuard',
  description: 'Advanced MCP server discovery and security analysis',
  icons: {
    icon: '/logo.png',
    shortcut: '/logo.png',
    apple: '/logo.png',
  },
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <div className="mx-auto max-w-5xl p-6">
          <header className="mb-8 border-b border-gray-800 pb-6 relative">
            {/* Dramatic background with geometric patterns */}
            <div className="absolute inset-0 bg-white rounded-lg -mx-6 -my-2 shadow-2xl">
              {/* Geometric pattern overlay */}
              <div className="absolute inset-0 opacity-10">
                <div className="absolute top-4 right-8 w-16 h-16 border-2 border-gray-400 rotate-45"></div>
                <div className="absolute top-2 right-12 w-6 h-6 border border-gray-500 rotate-12"></div>
                <div className="absolute bottom-4 left-8 w-12 h-12 border-2 border-gray-400 transform -rotate-45"></div>
                <div className="absolute bottom-2 left-12 w-4 h-4 border border-gray-500 rotate-30"></div>
                {/* Triangle patterns like in the image */}
                <div className="absolute top-6 left-1/2 w-0 h-0 border-l-8 border-r-8 border-b-12 border-l-transparent border-r-transparent border-b-gray-600 opacity-20"></div>
                <div className="absolute bottom-6 right-1/3 w-0 h-0 border-l-6 border-r-6 border-t-10 border-l-transparent border-r-transparent border-t-gray-500 opacity-15"></div>
              </div>
            </div>
            
            <div className="relative z-10 p-6 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                {/* Logo directly next to text */}
                <img 
                  src="/logo.png" 
                  alt="AgentAgentGo Logo" 
                  className="w-20 h-20 object-contain drop-shadow-lg"
                />
                <div>
                  <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-800 via-gray-900 to-gray-800 bg-clip-text text-transparent tracking-tight drop-shadow-sm">
                    AgentAgentGo
                  </h1>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className="text-xl font-bold text-gray-800 tracking-wide">MCPGuard</span>
                  </div>
                </div>
              </div>
              <nav className="flex items-center space-x-4">
                <a 
                  href="/" 
                  className="px-6 py-3 text-sm font-bold text-white bg-gray-600 hover:bg-gray-700 rounded-lg border-2 border-gray-500 hover:border-gray-600 transition-all shadow-lg hover:shadow-xl"
                >
                  HOME
                </a>
                <a 
                  href="/admin" 
                  className="px-6 py-3 text-sm font-bold text-white bg-gray-600 hover:bg-gray-700 rounded-lg border-2 border-gray-500 hover:border-gray-600 transition-all shadow-lg hover:shadow-xl"
                >
                  ADMIN
                </a>
              </nav>
            </div>
            <div className="relative z-10 px-6 mt-2 flex items-center space-x-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                <div className="w-2 h-2 bg-gray-600 rounded-full"></div>
              </div>
              <p className="text-gray-700 text-sm font-medium max-w-3xl">
                Advanced MCP server discovery and security analysis • Dual-mode architecture for humans and AI assistants
              </p>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  )
}


