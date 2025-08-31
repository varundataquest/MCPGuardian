/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable SWC to avoid macOS code signature issues
  swcMinify: false,
  compiler: {
    // Use Babel instead of SWC
    styledComponents: true,
  },
  experimental: {
    // Fallback for SWC issues on macOS
    forceSwcTransforms: false,
  },
};

export default nextConfig;


