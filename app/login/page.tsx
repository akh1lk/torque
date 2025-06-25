import { LoginForm } from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-slate-900 to-blue-900 bg-clip-text text-transparent">
            Torque
          </h1>
          <p className="text-slate-600 mt-2 text-sm">
            Professional 3D Scanning Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-slate-900">
              Welcome back
            </h2>
            <p className="text-slate-600 mt-1">
              Log in to explore your 3D scans
            </p>
          </div>

          <LoginForm />
        </div>

        {/* Footer */}
        <div className="text-center mt-6 text-sm text-slate-500">
          <p>
            By continuing, you agree to our{" "}
            <a href="#" className="text-blue-600 hover:text-blue-700">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="#" className="text-blue-600 hover:text-blue-700">
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </main>
  );
}
