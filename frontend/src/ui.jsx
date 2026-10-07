import {useCallback,useEffect,useState} from 'react'
import {api,errMsg} from './api.js'

export const inr = n => '₹' + Number(n || 0).toLocaleString('en-IN')

export function useApi(path) {
  const [s, set] = useState({data: null, loading: true, error: ''})
  const load = useCallback(async () => {
    try { const r = await api.get(path); set({data: r.data, loading: false, error: ''}) }
    catch (e) { set({data: null, loading: false, error: errMsg(e)}) }
  }, [path])
  useEffect(() => { load() }, [load])
  return {...s, reload: load}
}

export function Status({loading, error, reload}) {
  if (loading) return <p className="p-8 text-ink-soft" role="status">Loading…</p>
  return (<div className="rounded-3xl bg-white p-6" role="alert">
    <p className="font-semibold text-rose-600">{error}</p>
    <button onClick={reload} className="mt-3 rounded-full bg-sky-500 text-white text-sm font-semibold px-5 py-2">Try again</button></div>)
}

export const Banner = ({children}) => children ? <p role="alert" className="rounded-2xl bg-rose-50 text-rose-700 text-sm px-4 py-2">{children}</p> : null
