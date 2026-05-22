/**
 * Supabase Realtime hook — subscribes to live DB changes
 * Replaces polling; React dashboard receives trade/portfolio
 * updates the instant ZEUS writes to Postgres.
 *
 * Usage (once SUPABASE_URL + SUPABASE_ANON_KEY are set):
 *   const { trades, portfolioState, agentHealth } = useSupabaseRealtime()
 */

import { useState, useEffect, useRef } from 'react'

const SUPABASE_URL      = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

export default function useSupabaseRealtime() {
  const [trades, setTrades]               = useState([])
  const [decisionTraces, setTraces]       = useState([])
  const [portfolioState, setPortfolio]    = useState(null)
  const [agentHealth, setAgentHealth]     = useState([])
  const [connected, setConnected]         = useState(false)
  const clientRef = useRef(null)

  useEffect(() => {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
      console.warn('[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set — realtime disabled')
      return
    }

    // Lazy-load supabase-js (listed in package.json)
    let channel
    import('@supabase/supabase-js').then(({ createClient }) => {
      const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
      clientRef.current = supabase

      // ── Initial data fetch ─────────────────────────────────
      supabase.from('trades').select('*').order('recorded_at', { ascending: false }).limit(50)
        .then(({ data }) => data && setTrades(data))

      supabase.from('decision_traces').select('*').order('timestamp', { ascending: false }).limit(50)
        .then(({ data }) => data && setTraces(data))

      supabase.from('portfolio_state').select('*').order('refreshed_at', { ascending: false }).limit(1)
        .then(({ data }) => data?.[0] && setPortfolio(data[0]))

      supabase.from('agent_health').select('*').order('checked_at', { ascending: false }).limit(20)
        .then(({ data }) => data && setAgentHealth(data))

      // ── Realtime subscriptions ─────────────────────────────
      channel = supabase.channel('pantheon-live')

        // New trade placed
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'trades' }, ({ new: row }) => {
          setTrades(prev => [row, ...prev].slice(0, 200))
        })

        // Trade outcome backfilled by Argus
        .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'trades' }, ({ new: row }) => {
          setTrades(prev => prev.map(t => t.trade_id === row.trade_id ? row : t))
        })

        // Decision trace (every pipeline run)
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'decision_traces' }, ({ new: row }) => {
          setTraces(prev => [row, ...prev].slice(0, 200))
        })
        .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'decision_traces' }, ({ new: row }) => {
          setTraces(prev => prev.map(t => t.trace_id === row.trace_id ? row : t))
        })

        // Portfolio state (Argus refreshes every cycle)
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'portfolio_state' }, ({ new: row }) => {
          setPortfolio(row)
        })

        // Agent health
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_health' }, ({ new: row }) => {
          setAgentHealth(prev => {
            const filtered = prev.filter(a => a.agent_name !== row.agent_name)
            return [row, ...filtered].slice(0, 20)
          })
        })

        .subscribe((status) => {
          setConnected(status === 'SUBSCRIBED')
        })
    })

    return () => {
      channel?.unsubscribe()
    }
  }, [])

  return { trades, decisionTraces, portfolioState, agentHealth, connected }
}
