import {useRef,useState} from 'react'
import {Upload,Download,X,FileSpreadsheet,CheckCircle2} from 'lucide-react'
import {api,errMsg} from '../api.js'
import {Banner} from '../ui.jsx'

const csvCell=v=>/[",\n]/.test(v)?`"${String(v).replace(/"/g,'""')}"`:v

function downloadTemplate(entity,cols,sample){
  const text='﻿'+[cols.map(c=>c.l),sample].map(r=>r.map(csvCell).join(',')).join('\r\n')+'\r\n'  // BOM so Excel reads UTF-8
  const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}))
  const a=Object.assign(document.createElement('a'),{href:url,download:`smartbiz-${entity}-template.csv`})
  document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)
}

export default function ImportCsv({entity,title,cols,sample,onClose,onImported}){
  const [file,setFile]=useState(null),[res,setRes]=useState(null),[err,setErr]=useState(''),[busy,setBusy]=useState(false),[done,setDone]=useState(null)
  const input=useRef()
  const label=Object.fromEntries(cols.map(c=>[c.k,c.l]))
  const send=async(f,commit)=>{
    const fd=new FormData();fd.append('file',f)
    return (await api.post(`/import/${entity}?commit=${commit}`,fd,{timeout:120000})).data
  }
  const pick=async f=>{
    setErr('');setRes(null);setDone(null);setFile(f||null)
    if(!f){if(input.current)input.current.value='';return}
    if(f.size>5*1024*1024){setErr('File is larger than 5 MB. Split it into smaller files.');return}
    setBusy(true)
    try{setRes(await send(f,false))}catch(e){setErr(errMsg(e))}finally{setBusy(false)}
  }
  const confirmImport=async()=>{
    setErr('');setBusy(true)
    try{const r=await send(file,true);setDone(r);setRes(null);setFile(null);if(input.current)input.current.value='';await onImported()}
    catch(e){setErr(errMsg(e))}finally{setBusy(false)}
  }
  const toSave=res?res.created+res.updated:0
  return(<div className="rounded-3xl bg-white/85 shadow-sm shadow-sky-200/60 p-5 space-y-4">
    <div className="flex items-start justify-between gap-3">
      <div><h2 className="font-bold flex items-center gap-2"><FileSpreadsheet size={18} className="text-sky-500"/>Import {title.toLowerCase()} from CSV</h2>
        <p className="text-sm text-ink-soft mt-1">Columns: {cols.map(c=>c.l+(c.opt?' (optional)':'')).join(', ')}. Headers like "Customer Name", "Mobile" or "Qty" are matched automatically.
          From Excel use File, Save As, CSV.</p></div>
      <button onClick={onClose} aria-label="Close import" className="text-ink-soft hover:text-ink"><X size={18}/></button></div>
    <div className="flex flex-wrap gap-2">
      <label className={`flex items-center gap-2 rounded-full bg-sky-500 text-white text-sm font-semibold px-5 py-2 cursor-pointer ${busy?'opacity-60 pointer-events-none':''}`}>
        <Upload size={16}/>{file?'Choose another file':'Choose CSV file'}
        <input ref={input} type="file" accept=".csv,.tsv,.txt,text/csv" className="sr-only" onChange={e=>pick(e.target.files[0])}/></label>
      <button type="button" onClick={()=>downloadTemplate(entity,cols,sample)} className="flex items-center gap-2 rounded-full bg-sky-50 text-sky-600 text-sm font-semibold px-5 py-2 hover:bg-sky-100"><Download size={16}/>Download template</button>
      {file&&<span className="self-center text-sm text-ink-soft truncate max-w-60">{file.name}</span>}</div>
    {busy&&<p role="status" className="text-sm text-ink-soft">Reading file…</p>}
    <Banner>{err}</Banner>
    {done&&<p role="status" className="flex items-center gap-2 rounded-2xl bg-emerald-50 text-emerald-700 text-sm px-4 py-2"><CheckCircle2 size={16}/>
      Imported {done.created} new{done.updated?`, updated ${done.updated}`:''}{done.skipped?`, skipped ${done.skipped} already in your list`:''}{done.error_count?`, ${done.error_count} row(s) had errors and were left out`:''}.</p>}
    {res&&<div className="space-y-3">
      <p className="text-sm"><b>{res.total_rows}</b> rows found: <b>{res.created}</b> new{res.updated?<>, <b>{res.updated}</b> will update existing (same SKU)</>:null}
        {res.skipped?<>, <b>{res.skipped}</b> already in your list (skipped)</>:null}{res.error_count?<>, <b className="text-rose-600">{res.error_count}</b> with errors</>:null}.</p>
      <div className="flex flex-wrap gap-2 text-xs">{Object.entries(res.columns).map(([h,f])=>(
        <span key={h} className={`rounded-full px-3 py-1 ${f?'bg-sky-100':'bg-gray-100 text-ink-soft line-through'}`} title={f?`Used as ${label[f]}`:'Not used'}>{h}{f&&<> → <b>{label[f]}</b></>}</span>))}</div>
      {res.preview.length>0&&<div className="overflow-x-auto"><table className="w-full text-xs">
        <thead className="text-left text-ink-soft"><tr><th className="p-2">Row</th>{cols.map(c=><th key={c.k} className="p-2">{c.l}</th>)}<th className="p-2"/></tr></thead>
        <tbody>{res.preview.map(r=><tr key={r.row} className="border-t border-sky-50"><td className="p-2 text-ink-soft">{r.row}</td>
          {cols.map(c=><td key={c.k} className="p-2">{String(r[c.k]??'')}</td>)}<td className="p-2 text-ink-soft">{r.action==='update'?'update':'new'}</td></tr>)}</tbody></table>
        {toSave>res.preview.length&&<p className="text-xs text-ink-soft px-2">Showing the first {res.preview.length} rows.</p>}</div>}
      {res.errors.length>0&&<details open={res.errors.length<=5} className="rounded-2xl bg-rose-50 text-rose-700 text-xs p-3"><summary className="cursor-pointer font-semibold">Rows that will be left out</summary>
        <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">{res.errors.map(e=><li key={e.row}>Row {e.row}: {e.message}</li>)}</ul>
        {res.error_count>res.errors.length&&<p className="mt-1">…and {res.error_count-res.errors.length} more.</p>}</details>}
      <div className="flex gap-2">
        <button disabled={busy||!toSave} onClick={confirmImport} className="rounded-full bg-ink text-white text-sm font-semibold px-6 py-2.5 disabled:opacity-50">
          {toSave?`Import ${toSave} row${toSave>1?'s':''}`:'Nothing to import'}</button>
        <button onClick={()=>pick(null)} className="rounded-full text-sm font-semibold px-5 text-ink-soft hover:text-ink">Cancel</button></div></div>}
  </div>)
}
