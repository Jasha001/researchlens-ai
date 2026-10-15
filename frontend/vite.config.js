import{defineConfig}from'vite';
import react from'@vitejs/plugin-react';
export default defineConfig({plugins:[react()],server:{host:'127.0.0.1',proxy:Object.fromEntries(['/session','/authorize','/ai-status','/analyze','/ask','/understand','/research-gaps','/compare','/health','/explain','/healthcare','/comparison','/feedback'].map(x=>[x,'http://127.0.0.1:8182']))}});
