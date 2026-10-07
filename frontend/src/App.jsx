import {createContext,useContext,useState} from 'react'
import {Routes,Route,Navigate,NavLink,Outlet,useNavigate} from 'react-router-dom'
import {LayoutDashboard,ShoppingBag,Users,Package,Truck,Receipt,Sparkles,LogOut} from 'lucide-react'
import {api} from './api.js'
import Landing from './pages/Landing.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Orders from './pages/Orders.jsx'
import {Customers,Products,Suppliers,Expenses} from './pages/Lists.jsx'
import Assistant from './pages/Assistant.jsx'

const Auth=createContext()
export const useAuth=()=>useContext(Auth)

const nav=[['/app','Dashboard',LayoutDashboard],['/app/orders','Orders',ShoppingBag],['/app/customers','Customers',Users],
['/app/products','Inventory',Package],['/app/suppliers','Suppliers',Truck],['/app/expenses','Expenses',Receipt],['/app/assistant','Ask SmartBiz',Sparkles]]

function Shell(){
  const {user,logout}=useAuth(),go=useNavigate()
  if(!user)return <Navigate to="/login" replace/>
  return(<div className="min-h-screen md:flex bg-[#f4f6fc]">
    <aside className="md:w-60 md:min-h-screen bg-white border-r border-sky-100 p-4 flex md:flex-col gap-1 overflow-x-auto">
      <div className="hidden md:block px-3 py-4 text-xl font-extrabold">Smart<span className="text-sky-600">Biz</span></div>
      {nav.map(([to,label,Icon])=>(
        <NavLink key={to} to={to} end={to==='/app'} className={({isActive})=>`flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-semibold whitespace-nowrap ${isActive?'bg-sky-500 text-white':'text-ink-soft hover:bg-sky-50'}`}>
          <Icon size={18}/>{label}</NavLink>))}
      <p className="hidden md:block md:mt-auto px-4 pb-1 text-xs text-ink-soft truncate">{user.name} · {user.role}</p>
      <button onClick={()=>{logout();go('/login')}} className="flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-semibold text-ink-soft hover:bg-sky-50"><LogOut size={18}/>Log out</button>
    </aside>
    <main className="flex-1 p-5 md:p-8 max-w-6xl"><Outlet/></main></div>)
}

export default function App(){
  const [user,setUser]=useState(()=>JSON.parse(localStorage.getItem('sb_user')||'null'))
  const save=({access_token,user})=>{localStorage.setItem('sb_token',access_token);localStorage.setItem('sb_user',JSON.stringify(user));setUser(user)}
  const login=async(email,password)=>save((await api.post('/auth/login',{email,password})).data)
  const register=async(name,email,password)=>save((await api.post('/auth/register',{name,email,password})).data)
  const logout=()=>{localStorage.removeItem('sb_token');localStorage.removeItem('sb_user');setUser(null)}
  return(<Auth.Provider value={{user,login,register,logout}}><Routes>
    <Route path="/login" element={user?<Navigate to="/app" replace/>:<Login/>}/>
    <Route path="/" element={<Landing/>}/>
    <Route path="/app" element={<Shell/>}>
      <Route index element={<Dashboard/>}/><Route path="orders" element={<Orders/>}/>
      <Route path="customers" element={<Customers/>}/><Route path="products" element={<Products/>}/>
      <Route path="suppliers" element={<Suppliers/>}/><Route path="expenses" element={<Expenses/>}/>
      <Route path="assistant" element={<Assistant/>}/></Route>
  </Routes></Auth.Provider>)
}
