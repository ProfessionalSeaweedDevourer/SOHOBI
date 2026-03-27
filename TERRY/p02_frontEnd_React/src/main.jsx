import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import MapApp from './MapApp.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MapApp />
  </StrictMode>,
)
