import {useState} from 'react'
import {Search,Plus,Trash2} from 'lucide-react'
import {api,errMsg} from '../api.js'
import {useApi,Status,Banner,inr} from '../ui.jsx'
import {useAuth} from '../App.jsx'

// col: k = API field, l = label, t = text|num|money|date, opt = optional in the form, ro = display only
function List({title,noun,path,cols}){
  const {data,loading,error,reload}=useApi(path),{user}=useAuth()
  const [q,setQ]=useState(''),[adding,setAdding]=useState(false),[draft,setDraft]=useState({}),[msg,setMsg]=useState('')
  if(!data)return <Status {...{loading,error,reload}}/>
  const fields=cols.filter(c=>!c.ro)
  const shown=data.filter(r=>JSON.stringify(r).toLowerCase().includes(q.toLowerCase()))
  const run=async fn=>{setMsg('');try{await fn();await reload()}catch(x){setMsg(errMsg(x))}}
  const save=e=>{e.preventDefault()
    const body={};fields.forEach(f=>{const v=draft[f.k];if(v!==undefined&&v!=='')body[f.k]=['num','money'].includes(f.t)?+v:v})
    run(async()=>{await api.post(path,body);setDraft({});setAdding(false)})}
  const cell=(r,c)=>['money'].includes(c.t)?inr(r[c.k]):r[c.k]
  return(<div className="space-y-5"><div className="flex items-center justify-between gap-3 flex-wrap"><h1 className="text-2xl font-extrabold">{title}</h1>
    <div className="flex gap-3"><label className="flex items-center gap-2 rounded-full bg-white px-4 py-2"><Search size={16} className="text-sky-500"/>
      <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search" aria-label="Search" className="outline-none text-sm bg-transparent w-36"/></label>
      <button onClick={()=>setAdding(!adding)} className="flex items-center gap-1 rounded-full bg-sky-500 text-white text-sm font-semibold px-5"><Plus size={16}/>Add</button></div></div>
    <Banner>{msg}</Banner>
    {adding&&<form onSubmit={save} className="rounded-3xl bg-white/85 p-5 grid sm:grid-cols-3 gap-3">
      {fields.map(f=><input key={f.k} required={!f.opt} aria-label={f.l} title={f.l} placeholder={f.l+(f.opt?' (optional)':'')}
        type={f.t==='date'?'date':['num','money'].includes(f.t)?'number':'text'} min={['num','money'].includes(f.t)?0:undefined} step={f.t==='money'?'any':undefined}
        value={draft[f.k]||''} onChange={e=>setDraft({...draft,[f.k]:e.target.value})} className="rounded-full bg-sky-50 px-4 py-2.5 text-sm outline-none"/>)}
      <button className="rounded-full bg-ink text-white text-sm font-semibold py-2.5">Save {noun}</button></form>}
    <div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-2 overflow-x-auto"><table className="w-full text-sm">
      <thead className="text-left text-ink-soft"><tr>{cols.map(c=><th key={c.k} className="p-3 font-semibold">{c.l}</th>)}<th className="w-10"/></tr></thead>
      <tbody>{shown.map(r=><tr key={r.id} className="hover:bg-sky-50">{cols.map(c=><td key={c.k} className="p-3">{cell(r,c)}</td>)}
        <td className="p-3">{user.role==='admin'&&<button aria-label={`Delete ${r.name||r.title}`} onClick={()=>confirm(`Delete ${r.name||r.title}?`)&&run(()=>api.delete(`${path}/${r.id}`))} className="text-ink-soft hover:text-rose-600"><Trash2 size={16}/></button>}</td></tr>)}
      {!shown.length&&<tr><td className="p-6 text-ink-soft" colSpan={cols.length+1}>{data.length?'Nothing matches your search.':`No ${title.toLowerCase()} yet. Use Add to create the first one.`}</td></tr>}</tbody></table></div></div>)
}
export const Customers=()=><List title="Customers" noun="customer" path="/customers" cols={[{k:'name',l:'Name'},{k:'phone',l:'Phone',opt:1},{k:'city',l:'City',opt:1},{k:'due',l:'Amount due',t:'money',ro:1}]}/>
export const Products=()=><List title="Inventory" noun="product" path="/products" cols={[{k:'name',l:'Product'},{k:'sku',l:'SKU'},{k:'stock',l:'In stock',t:'num'},{k:'reorder_level',l:'Reorder level',t:'num'},{k:'price',l:'Price',t:'money'}]}/>
export const Suppliers=()=><List title="Suppliers" noun="supplier" path="/suppliers" cols={[{k:'name',l:'Name'},{k:'phone',l:'Phone',opt:1},{k:'item',l:'Supplies',opt:1}]}/>
export const Expenses=()=><List title="Expenses" noun="expense" path="/expenses" cols={[{k:'title',l:'Expense'},{k:'category',l:'Category',opt:1},{k:'amount',l:'Amount',t:'money'},{k:'date',l:'Date',t:'date',opt:1}]}/>
