import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, LogIn, AlertCircle, Shield, Eye, EyeOff } from 'lucide-react';
import './Login.css';

const Login = () => {
  const [step, setStep] = useState(1); // 1: credentials, 2: OTP
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    otp_code: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [otpRequired, setOtpRequired] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validation
    if (!formData.username || !formData.password) {
      setError('يرجى إدخال اسم المستخدم وكلمة المرور');
      setLoading(false);
      return;
    }

    if (step === 2 && !formData.otp_code) {
      setError('يرجى إدخال رمز التحقق (OTP)');
      setLoading(false);
      return;
    }

    // Attempt login
    const result = await login(
      formData.username, 
      formData.password,
      step === 2 ? formData.otp_code : undefined
    );
    
    if (result.success) {
      // Successful login
      navigate('/dashboard');
    } else if (result.otpRequired) {
      // OTP is required - move to step 2
      setOtpRequired(true);
      setStep(2);
      setError('');
    } else {
      // Login failed
      setError(result.message || 'فشل تسجيل الدخول. يرجى التحقق من اسم المستخدم وكلمة المرور.');
    }
    
    setLoading(false);
  };

  const handleBackToCredentials = () => {
    setStep(1);
    setOtpRequired(false);
    setFormData({
      ...formData,
      otp_code: ''
    });
    setError('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
              {step === 1 ? (
                <LogIn className="w-8 h-8 text-white" />
              ) : (
                <Shield className="w-8 h-8 text-white" />
              )}
            </div>
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                {step === 1 ? 'تسجيل الدخول' : 'التحقق الثنائي (OTP)'}
              </CardTitle>
              <CardDescription className="text-gray-600 mt-2">
                {step === 1 
                  ? 'نظام الشكاوى الإلكتروني' 
                  : 'أدخل رمز التحقق من تطبيق المصادقة'
                }
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <Alert variant="destructive" className="border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-800">
                    {error}
                  </AlertDescription>
                </Alert>
              )}
              
              {step === 1 ? (
                <>
                  {/* Username Field */}
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-sm font-medium text-gray-700">
                      اسم المستخدم
                    </Label>
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      value={formData.username}
                      onChange={handleChange}
                      placeholder="أدخل اسم المستخدم"
                      className="h-11 text-right"
                      disabled={loading}
                      autoComplete="username"
                      dir="ltr"
                      required
                    />
                  </div>
                  
                  {/* Password Field */}
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                      كلمة المرور
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        name="password"
                        type={showPassword ? "text" : "password"}
                        value={formData.password}
                        onChange={handleChange}
                        placeholder="أدخل كلمة المرور"
                        className="h-11 text-right pr-10"
                        disabled={loading}
                        autoComplete="current-password"
                        dir="ltr"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition-colors"
                        tabIndex={-1}
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {/* OTP Field */}
                  <div className="space-y-2">
                    <Label htmlFor="otp_code" className="text-sm font-medium text-gray-700">
                      رمز التحقق (OTP)
                    </Label>
                    <Input
                      id="otp_code"
                      name="otp_code"
                      type="text"
                      value={formData.otp_code}
                      onChange={handleChange}
                      placeholder="123456"
                      className="h-11 text-center text-2xl tracking-widest font-mono"
                      disabled={loading}
                      maxLength={6}
                      pattern="[0-9]{6}"
                      autoComplete="one-time-code"
                      dir="ltr"
                      required
                      autoFocus
                    />
                    <p className="text-xs text-gray-500 text-center">
                      أدخل الرمز المكون من 6 أرقام من تطبيق المصادقة
                    </p>
                  </div>

                  {/* Info about logged in user */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                    <p className="text-sm text-blue-800">
                      تسجيل الدخول لـ: <span className="font-semibold">{formData.username}</span>
                    </p>
                  </div>
                </>
              )}
              
              <div className="space-y-3">
                <Button 
                  type="submit" 
                  className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.02]"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {step === 1 ? 'جاري تسجيل الدخول...' : 'جاري التحقق...'}
                    </>
                  ) : (
                    step === 1 ? 'تسجيل الدخول' : 'تحقق من الرمز'
                  )}
                </Button>

                {step === 2 && (
                  <Button 
                    type="button"
                    variant="outline"
                    className="w-full h-11"
                    onClick={handleBackToCredentials}
                    disabled={loading}
                  >
                    العودة إلى الخطوة السابقة
                  </Button>
                )}
              </div>

              {step === 1 && (
                <div className="text-center">
                  <p className="text-xs text-gray-500">
                    في حالة نسيان كلمة المرور، يرجى التواصل مع المسؤول
                  </p>
                </div>
              )}
            </form>
          </CardContent>
        </Card>
        
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            © 2024 نظام الشكاوى الإلكتروني. جميع الحقوق محفوظة.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
