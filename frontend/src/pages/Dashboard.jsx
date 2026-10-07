import {AreaChart,Area,XAxis,YAxis,Tooltip,ResponsiveContainer} from 'recharts'
import {useApi,Status,inr} from '../ui.jsx'

export default function Dashboard(){
  const {data:d,loading,error,reload}=useApi('/dashboard')
  if(!d)return <Status {...{loading,error,reload}}/>
  const stats=[['Total sales',inr(d.total_sales)],['Active orders',d.active_orders],['Pending payments',inr(d.pending_payments)],
    ['Low-stock products',d.low_stock.length],['Expenses',inr(d.expenses)],['Estimated profit',inr(d.estimated_profit)]]
  return(<div className="space-y-6"><h1 className="text-2xl font-extrabold">Dashboard</h1>
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">{stats.map(([l,v],i)=>(
      <div key={l} className={`rounded-3xl p-5 ${i===5?'bg-ink text-white':'bg-white/85 shadow-sm shadow-sky-200/60'}`}>
        <p className={`text-xs font-semibold ${i===5?'text-sky-200':'text-ink-soft'}`}>{l}</p><p className="text-2xl font-extrabold mt-1">{v}</p></div>))}</div>
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5"><h2 className="font-bold mb-3">Orders in the last 7 days</h2>
        <ResponsiveContainer width="100%" height={220}><AreaChart data={d.weekly_orders}>
          <XAxis dataKey="d" axisLine={false} tickLine={false}/><YAxis hide allowDecimals={false}/><Tooltip/>
          <Area dataKey="v" name="Orders" stroke="#3f69cc" fill="#c5d6fb" strokeWidth={3}/></AreaChart></ResponsiveContainer></div>
      <div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5"><h2 className="font-bold mb-3">Restock soon</h2>
        {d.low_stock.length?d.low_stock.map(p=><div key={p.id} className="flex justify-between py-2 text-sm border-b border-sky-50"><span>{p.name}</span>
          <span className="font-bold text-rose-500">{p.stock} left</span></div>):<p className="text-sm text-ink-soft">Every product is above its reorder level.</p>}</div></div></div>)
}
