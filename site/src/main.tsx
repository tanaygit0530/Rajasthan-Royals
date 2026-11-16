import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import Gate from './components/Gate'
import Layout from './components/Layout'
import { DataProvider } from './lib/data'
import Landing from './pages/Landing'
import Rankings from './pages/Rankings'
import PlayerPage from './pages/Player'
import Compare from './pages/Compare'
import How from './pages/How'
import Strategy from './pages/Strategy'
import Report from './pages/Report'
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Gate><DataProvider><HashRouter><Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} /><Route path="rankings" element={<Rankings />} />
        <Route path="player/:id" element={<PlayerPage />} /><Route path="compare" element={<Compare />} />
        <Route path="how-it-works" element={<How />} /><Route path="strategy" element={<Strategy />} />
        <Route path="report" element={<Report />} />
        <Route path="*" element={<div className="py-16 text-center text-ink2">Page not found. <a className="text-royal underline" href="#/">Go to the overview</a>.</div>} />
      </Route>
    </Routes></HashRouter></DataProvider></Gate>
  </React.StrictMode>)
