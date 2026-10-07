import {useState} from 'react'
import {Check,Plus,Trash2} from 'lucide-react'
import {api,errMsg} from '../api.js'
import {useApi,Status,Banner,inr} from '../ui.jsx'
import {useAuth} from '../App.jsx'

const STAGES=['New','Confirmed','In Production','Ready','Delivered']
const field='rounded-full bg-sky-50 px-4 py-2.5 text-sm outline-none'
const card='rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60'

function NewOrder({onDone}){
  const cu=useApi('/customers'),pr=useApi('/products')
  const [customer,setCustomer]=useState(''),[rows,setRows]=useState([{product_id:'',qty:1}]),[advance,setAdvance]=useState(''),[err,setErr]=useState('')
  if(!cu.data||!pr.data)return <Status loading={cu.loading||pr.loading} error={cu.error||pr.error} reload={()=>{cu.reload();pr.reload()}}/>
  const price=id=>pr.data.find(p=>p.id===+id)?.price||0
  const total=rows.reduce((a,r)=>a+price(r.product_id)*(+r.qty||0),0)
  const setRow=(i,patch)=>setRows(rows.map((r,j)=>j===i?{...r,...patch}:r))
  const submit=async e=>{e.preventDefault();setErr('')
    try{await api.post('/orders',{customer_id:+customer,items:rows.map(r=>({product_id:+r.product_id,qty:+r.qty})),advance:+advance||0});onDone()}
    catch(x){setErr(errMsg(x))}}
  return(<form onSubmit={submit} className={`${card} p-5 space-y-3`}>
    <select required value={customer} onChange={e=>setCustomer(e.target.value)} className={`${field} w-full`} aria-label="Customer">
      <option value="">Select customer</option>{cu.data.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
    {rows.map((r,i)=>(<div key={i} className="flex gap-2">
      <select required value={r.product_id} onChange={e=>setRow(i,{product_id:e.target.value})} className={`${field} flex-1 min-w-0`} aria-label="Product">
        <option value="">Select product</option>{pr.data.map(p=><option key={p.id} value={p.id}>{p.name} ({p.stock} in stock)</option>)}</select>
      <input required type="number" min="1" value={r.qty} onChange={e=>setRow(i,{qty:e.target.value})} className={`${field} w-24`} aria-label="Quantity"/>
      {rows.length>1&&<button type="button" aria-label="Remove item" onClick={()=>setRows(rows.filter((_,j)=>j!==i))} className="px-2 text-ink-soft"><Trash2 size={16}/></button>}</div>))}
    <button type="button" onClick={()=>setRows([...rows,{product_id:'',qty:1}])} className="text-sm font-semibold text-sky-600">+ Add another product</button>
    <div className="flex flex-wrap items-center gap-3">
      <input type="number" min="0" max={total} step="any" placeholder="Advance received (₹)" value={advance} onChange={e=>setAdvance(e.target.value)} className={field} aria-label="Advance"/>
      <p className="text-sm font-semibold">Total {inr(total)}</p>
      <button className="ml-auto rounded-full bg-ink text-white text-sm font-semibold px-6 py-2.5">Create order</button></div>
    <Banner>{err}</Banner></form>)
}

export default function Orders(){
  const {data:orders,loading,error,reload}=useApi('/orders')
  const {user}=useAuth()
  const [sel,setSel]=useState(null),[msg,setMsg]=useState(''),[creating,setCreating]=useState(false),[amt,setAmt]=useState('')
  if(!orders)return <Status {...{loading,error,reload}}/>
  const o=orders.find(x=>x.id===sel)||orders[0]
  const act=async fn=>{setMsg('');try{await fn();await reload()}catch(e){setMsg(errMsg(e))}}
  return(<div className="space-y-6">
    <div className="flex items-center justify-between"><h1 className="text-2xl font-extrabold">Orders</h1>
      <button onClick={()=>setCreating(!creating)} className="flex items-center gap-1 rounded-full bg-sky-500 text-white text-sm font-semibold px-5 py-2"><Plus size={16}/>New order</button></div>
    {creating&&<NewOrder onDone={()=>{setCreating(false);setSel(null);reload()}}/>}
    <Banner>{msg}</Banner>
    {!o?<p className="text-ink-soft">No orders yet. Add customers and products first, then create your first order.</p>:<>
    <div className={`${card} p-6 space-y-5`}>
      <div className="flex justify-between flex-wrap gap-3"><div><p className="font-bold">{o.code} · {o.customer}</p>
        <p className="text-sm text-ink-soft">Received {inr(o.paid)} of {inr(o.total)}. Pending {inr(o.pending)}</p></div>
        <button disabled={o.stage===4} onClick={()=>act(()=>api.post(`/orders/${o.id}/advance`))} className="rounded-full bg-sky-500 disabled:bg-sky-200 text-white text-sm font-semibold px-6 py-2">
          {o.stage===4?'Delivered':`Move to ${STAGES[o.stage+1]}`}</button></div>
      <ol className="flex items-center overflow-x-auto">{STAGES.map((s,i)=>(<li key={s} className="flex items-center flex-1 min-w-fit">
        <span className={`grid place-items-center size-8 rounded-full text-xs font-bold ${i<=o.stage?'bg-sky-500 text-white':'bg-sky-100 text-ink-soft'}`}>{i<o.stage?<Check size={16}/>:i+1}</span>
        <span className={`mx-2 text-sm ${i===o.stage?'font-bold':'text-ink-soft'}`}>{s}</span>
        {i<4&&<span className={`flex-1 h-0.5 min-w-4 ${i<o.stage?'bg-sky-500':'bg-sky-100'}`}/>}</li>))}</ol>
      <p className="text-sm text-ink-soft">{o.items.map(i=>`${i.qty} × ${i.product}`).join(', ')}</p>
      <div className="flex flex-wrap items-center gap-3">
        {o.pending>0&&<form className="flex gap-2" onSubmit={e=>{e.preventDefault();act(async()=>{await api.post(`/orders/${o.id}/payments`,{amount:+amt});setAmt('')})}}>
          <input required type="number" min="1" step="any" max={o.pending} value={amt} onChange={e=>setAmt(e.target.value)} placeholder={`Payment (max ${o.pending})`} className={field} aria-label="Payment amount"/>
          <button className="rounded-full bg-ink text-white text-sm font-semibold px-5">Record payment</button></form>}
        {user.role==='admin'&&<button onClick={()=>confirm(`Delete ${o.code}? Stock for undelivered orders is returned.`)&&act(async()=>{await api.delete(`/orders/${o.id}`);setSel(null)})} className="ml-auto text-sm font-semibold text-rose-600">Delete order</button>}</div>
      {o.payments.length>0&&<ul className="text-sm text-ink-soft space-y-1">{o.payments.map((p,i)=><li key={i}>{inr(p.amount)} {p.note&&`· ${p.note}`} · {new Date(p.paid_at).toLocaleDateString('en-IN')}</li>)}</ul>}</div>
    <div className={`${card} p-2 overflow-x-auto`}><table className="w-full text-sm">
      <thead className="text-left text-ink-soft"><tr>{['Order','Customer','Stage','Total','Pending'].map(h=><th key={h} className="p-3 font-semibold">{h}</th>)}</tr></thead>
      <tbody>{orders.map(x=>(<tr key={x.id} onClick={()=>setSel(x.id)} className={`cursor-pointer hover:bg-sky-50 ${x.id===o.id?'bg-sky-50':''}`}>
        <td className="p-3 font-semibold">{x.code}</td><td className="p-3">{x.customer}</td>
        <td className="p-3"><span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold">{x.stage_name}</span></td>
        <td className="p-3">{inr(x.total)}</td><td className={`p-3 font-semibold ${x.pending?'text-rose-500':'text-sky-600'}`}>{inr(x.pending)}</td></tr>))}</tbody></table></div></>}</div>)
}
