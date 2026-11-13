import {Link} from 'react-router-dom'
import {Users,Package,ShoppingBag,Upload} from 'lucide-react'
import {AreaChart,Area,XAxis,YAxis,Tooltip,ResponsiveContainer} from 'recharts'
import {useApi,Status,inr} from '../ui.jsx'
import {useAuth} from '../App.jsx'

function GetStarted({counts}){
  const steps=[['/app/customers','Add your customers',Users,counts.customers],['/app/products','Add your products and stock',Package,counts.products],
    ['/app/orders','Create your first order',ShoppingBag,counts.orders]]
  return(<div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-6 space-y-4">
    <div><h2 className="text-lg font-bold">Your dashboard is ready</h2>
      <p className="text-sm text-ink-soft mt-1">This is your own workspace. Nobody else sees your data. Add records one by one, or use <b>Import CSV</b> on the Customers, Inventory, Suppliers and Expenses pages to bring in an existing Excel sheet.</p></div>
    <ol className="grid sm:grid-cols-3 gap-3">{steps.map(([to,t,Icon,n],i)=>(
      <li key={to}><Link to={to} className={`flex items-center gap-3 rounded-2xl p-4 text-sm font-semibold ${n?'bg-sky-50 text-ink-soft line-through':'bg-sky-100 hover:bg-sky-200'}`}>
        <span className="grid place-items-center size-9 shrink-0 rounded-full bg-white text-sky-600"><Icon size={18}/></span>{i+1}. {t}</Link></li>))}</ol>
    <p className="flex items-center gap-2 text-xs text-ink-soft"><Upload size={14}/>Tip: each import page has a "Download template" button with the right columns.</p></div>)
}

export default function Dashboard(){
  const {data:d,loading,error,reload}=useApi('/dashboard'),{user}=useAuth()
  if(!d)return <Status {...{loading,error,reload}}/>
  const fresh=!d.counts.orders||!d.counts.customers||!d.counts.products
  const stats=[['Total sales',inr(d.total_sales)],['Active orders',d.active_orders],['Pending payments',inr(d.pending_payments)],
    ['Low-stock products',d.low_stock.length],['Expenses',inr(d.expenses)],['Estimated profit',inr(d.estimated_profit)]]
  return(<div className="space-y-6"><div><h1 className="text-2xl font-extrabold">Dashboard</h1><p className="text-sm text-ink-soft">Welcome, {user.name}</p></div>
    {fresh&&<GetStarted counts={d.counts}/>}
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">{stats.map(([l,v],i)=>(
      <div key={l} className={`rounded-3xl p-5 ${i===5?'bg-ink text-white':'bg-white/85 shadow-sm shadow-sky-200/60'}`}>
        <p className={`text-xs font-semibold ${i===5?'text-sky-200':'text-ink-soft'}`}>{l}</p><p className={`text-2xl font-extrabold mt-1 ${i===5&&d.estimated_profit<0?'text-rose-300':''}`}>{v}</p></div>))}</div>
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5"><h2 className="font-bold mb-3">Orders in the last 7 days</h2>
        <ResponsiveContainer width="100%" height={220}><AreaChart data={d.weekly_orders}>
          <XAxis dataKey="d" axisLine={false} tickLine={false}/><YAxis hide allowDecimals={false} domain={[0,dataMax=>Math.max(dataMax,1)]}/><Tooltip/>
          <Area dataKey="v" name="Orders" stroke="#3f69cc" fill="#c5d6fb" strokeWidth={3}/></AreaChart></ResponsiveContainer></div>
      <div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5"><h2 className="font-bold mb-3">Restock soon</h2>
        {d.low_stock.length?d.low_stock.map(p=><div key={p.id} className="flex justify-between py-2 text-sm border-b border-sky-50"><span>{p.name}</span>
          <span className="font-bold text-rose-500">{p.stock} left</span></div>)
          :<p className="text-sm text-ink-soft">{d.counts.products?'Every product is above its reorder level.':'No products yet.'}</p>}</div></div></div>)
}
