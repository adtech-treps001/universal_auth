import LoginForm from '../components/organisms/LoginForm'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Universal Auth
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Secure, modern authentication for your applications. 
            Sign in with your preferred method and experience seamless security.
          </p>
        </div>
        
        <div className="flex justify-center">
          <LoginForm />
        </div>
        
        <div className="mt-8 text-center">
          <p className="text-sm text-slate-500">
            Protected by enterprise-grade security • SOC 2 Type II Compliant
          </p>
        </div>
      </div>
    </div>
  )
}