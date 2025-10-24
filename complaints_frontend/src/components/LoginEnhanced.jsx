import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Loader2, LogIn, Shield, Eye, EyeOff, ArrowRight, Clock,
  AlertTriangle, CheckCircle2, User, Key, Sparkles, WifiOff, Wifi
} from 'lucide-react';
import { toast } from '@/lib/toast';
import './Login.css';

const LoginEnhanced = () => {
  const [step, setStep] = useState('username'); // 'username', 'password', 'otp'
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    otp_code: '',
    remember_me: false
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [otpRequired, setOtpRequired] = useState(false);
  const [lockoutInfo, setLockoutInfo] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [redirectMessage, setRedirectMessage] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      toast.success('تم استعادة الاتصال بالإنترنت');
    };
    const handleOffline = () => {
      setIsOnline(false);
      toast.error('تم فقدان الاتصال بالإنترنت');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    const redirectReason = searchParams.get('redirect');
    if (redirectReason === 'session_expired') {
      setRedirectMessage('انتهت جلستك. يرجى تسجيل الدخول مرة أخرى');
      toast.warning('انتهت جلستك. يرجى تسجيل الدخول مرة أخرى');
    } else if (redirectReason === 'unauthorized') {
      setRedirectMessage('يجب تسجيل الدخول للوصول إلى هذه الصفحة');
      toast.info('يجب تسجيل الدخول للوصول إلى هذه الصفحة');
    }
  }, [searchParams]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
    setLockoutInfo(null);
  };

  const handleUsernameSubmit = (e) => {
    e.preventDefault();
    
    if (!formData.username || formData.username.trim().length < 2) {
      setError('يرجى إدخال اسم مستخدم صالح');
      toast.error('يرجى إدخال اسم مستخدم صالح');
      return;
    }
    
    setError('');
    setStep('password');
    toast.success('تم! الآن أدخل كلمة المرور');
  };

  const handleBackToUsername = () => {
    setStep('username');
    setFormData({
      ...formData,
      password: '',
      otp_code: ''
    });
    setError('');
    setLockoutInfo(null);
    setOtpRequired(false);
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!formData.password) {
      setError('يرجى إدخال كلمة المرور');
      toast.error('يرجى إدخال كلمة المرور');
      setLoading(false);
      return;
    }

    if (!isOnline) {
      setError('لا يوجد اتصال بالإنترنت');
      toast.error('لا يوجد اتصال بالإنترنت. يرجى التحقق من الاتصال');
      setLoading(false);
      return;
    }

    const toastId = toast.loading('جاري تسجيل الدخول...');

    try {
      const result = await login(
        formData.username, 
        formData.password,
        undefined,
        formData.remember_me
      );
      
      toast.dismiss(toastId);
      
      if (result.success) {
        toast.success(`مرحباً ${result.user?.full_name || formData.username}! 🎉`, { duration: 3000 });
        setTimeout(() => navigate('/dashboard'), 500);
      } else if (result.otpRequired) {
        setOtpRequired(true);
        setStep('otp');
        setError('');
        toast.info('يرجى إدخال رمز التحقق الثنائي');
      } else {
        handleLoginError(result);
      }
    } catch (err) {
      toast.dismiss(toastId);
      console.error('Login error:', err);
      setError('حدث خطأ في الاتصال بالخادم. يرجى المحاولة مرة أخرى');
      toast.error('حدث خطأ في الاتصال بالخادم');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (!formData.otp_code || formData.otp_code.length !== 6) {
      setError('يرجى إدخال رمز التحقق المكون من 6 أرقام');
      toast.error('يرجى إدخال رمز التحقق المكون من 6 أرقام');
      setLoading(false);
      return;
    }

    const toastId = toast.loading('جاري التحقق من الرمز...');

    try {
      const result = await login(
        formData.username, 
        formData.password,
        formData.otp_code,
        formData.remember_me
      );
      
      toast.dismiss(toastId);
      
      if (result.success) {
        toast.success(`تم التحقق بنجاح! مرحباً ${result.user?.full_name || formData.username} 🎉`);
        setTimeout(() => navigate('/dashboard'), 500);
      } else {
        handleLoginError(result);
      }
    } catch (err) {
      toast.dismiss(toastId);
      console.error('OTP verification error:', err);
      setError('حدث خطأ في التحقق من الرمز');
      toast.error('حدث خطأ في التحقق من الرمز');
    } finally {
      setLoading(false);
    }
  };

  const handleLoginError = (result) => {
    if (result.account_locked) {
      const lockoutTime = result.lockout_until;
      setLockoutInfo({
        locked: true,
        until: lockoutTime,
        attempts: result.failed_attempts
      });
      setError(result.message || 'تم قفل الحساب مؤقتاً بسبب محاولات دخول فاشلة متعددة');
      toast.error('تم قفل الحساب مؤقتاً', { duration: 6000 });
    } else if (result.failed_attempts) {
      const remainingAttempts = 5 - (result.failed_attempts || 0);
      setError(`${result.message || 'اسم المستخدم أو كلمة المرور غير صحيحة'}. المحاولات المتبقية: ${remainingAttempts}`);
      toast.warning(`محاولات متبقية: ${remainingAttempts}`, { duration: 4000 });
    } else {
      setError(result.message || 'فشل تسجيل الدخول. يرجى التحقق من البيانات والمحاولة مرة أخرى');
      toast.error('فشل تسجيل الدخول');
    }
  };

  const getStepIcon = () => {
    switch (step) {
      case 'username':
        return <User className="w-8 h-8 text-white" />;
      case 'password':
        return <Key className="w-8 h-8 text-white" />;
      case 'otp':
        return <Shield className="w-8 h-8 text-white" />;
      default:
        return <LogIn className="w-8 h-8 text-white" />;
    }
  };

  const getStepTitle = () => {
    switch (step) {
      case 'username':
        return 'تسجيل الدخول';
      case 'password':
        return `مرحباً، ${formData.username}`;
      case 'otp':
        return 'التحقق الثنائي';
      default:
        return 'تسجيل الدخول';
    }
  };

  const getStepDescription = () => {
    switch (step) {
      case 'username':
        return 'نظام الشكاوى الإلكتروني';
      case 'password':
        return 'أدخل كلمة المرور للمتابعة';
      case 'otp':
        return 'أدخل رمز التحقق من تطبيق المصادقة';
      default:
        return 'نظام الشكاوى الإلكتروني';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4">
      <div className="w-full max-w-md">
        {/* Connection Status */}
        {!isOnline && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 animate-pulse">
            <WifiOff className="w-5 h-5 text-red-600" />
            <p className="text-sm text-red-700 font-medium">لا يوجد اتصال بالإنترنت</p>
          </div>
        )}

        {/* Redirect Message */}
        {redirectMessage && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <p className="text-sm text-yellow-700">{redirectMessage}</p>
          </div>
        )}

        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-sm overflow-hidden">
          <CardHeader className="text-center space-y-4 pb-6 bg-gradient-to-br from-gray-50 to-white">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-lg animate-fadeIn">
              {getStepIcon()}
            </div>
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900 transition-all duration-300">
                {getStepTitle()}
              </CardTitle>
              <CardDescription className="text-gray-600 mt-2 transition-all duration-300">
                {getStepDescription()}
              </CardDescription>
            </div>

            {/* Step Indicator */}
            {step !== 'username' && (
              <div className="flex justify-center gap-2 pt-2">
                <div className={`h-1.5 w-8 rounded-full transition-colors ${step === 'username' ? 'bg-blue-600' : 'bg-blue-300'}`} />
                <div className={`h-1.5 w-8 rounded-full transition-colors ${step === 'password' || step === 'otp' ? 'bg-blue-600' : 'bg-gray-300'}`} />
                {otpRequired && <div className={`h-1.5 w-8 rounded-full transition-colors ${step === 'otp' ? 'bg-blue-600' : 'bg-gray-300'}`} />}
              </div>
            )}
          </CardHeader>
          
          <CardContent className="p-6">
            {/* Error Display */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 animate-fadeIn">
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-800">خطأ</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Lockout Warning */}
            {lockoutInfo && lockoutInfo.locked && (
              <div className="mb-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-orange-800">تم قفل الحساب مؤقتاً</p>
                    <p className="text-sm text-orange-700 mt-1">
                      تم تجاوز الحد الأقصى لمحاولات تسجيل الدخول. يرجى المحاولة مرة أخرى بعد {lockoutInfo.until} دقيقة.
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Username Step */}
            {step === 'username' && (
              <form onSubmit={handleUsernameSubmit} className="space-y-6 animate-fadeIn">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-sm font-medium text-gray-700">
                    اسم المستخدم
                  </Label>
                  <div className="relative">
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      value={formData.username}
                      onChange={handleChange}
                      placeholder="أدخل اسم المستخدم"
                      className="h-12 text-right pr-12 text-lg"
                      disabled={loading}
                      autoComplete="username"
                      dir="ltr"
                      required
                      autoFocus
                    />
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
                      <User className="w-5 h-5" />
                    </div>
                  </div>
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.02] shadow-lg"
                  disabled={loading || !isOnline}
                >
                  <span>التالي</span>
                  <ArrowRight className="mr-2 h-5 w-5 transform rotate-180" />
                </Button>
              </form>
            )}

            {/* Password Step */}
            {step === 'password' && (
              <form onSubmit={handlePasswordSubmit} className="space-y-6 animate-fadeIn">
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
                      className="h-12 text-right pr-12 pl-12 text-lg"
                      disabled={loading}
                      autoComplete="current-password"
                      dir="ltr"
                      required
                      autoFocus
                    />
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
                      <Key className="w-5 h-5" />
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition-colors"
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="remember_me"
                      checked={formData.remember_me}
                      onCheckedChange={(checked) => 
                        setFormData({ ...formData, remember_me: checked })
                      }
                      disabled={loading}
                    />
                    <Label 
                      htmlFor="remember_me" 
                      className="text-sm text-gray-600 cursor-pointer select-none"
                    >
                      تذكرني
                    </Label>
                  </div>
                  <button
                    type="button"
                    onClick={handleBackToUsername}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  >
                    تغيير المستخدم
                  </button>
                </div>
                
                <div className="space-y-3">
                  <Button 
                    type="submit" 
                    className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.02] shadow-lg"
                    disabled={loading || !isOnline || (lockoutInfo && lockoutInfo.locked)}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                        جاري التحقق...
                      </>
                    ) : (
                      <>
                        <Sparkles className="ml-2 h-5 w-5" />
                        تسجيل الدخول
                      </>
                    )}
                  </Button>
                </div>

                <div className="text-center">
                  <p className="text-xs text-gray-500">
                    في حالة نسيان كلمة المرور، يرجى التواصل مع المسؤول
                  </p>
                </div>
              </form>
            )}

            {/* OTP Step */}
            {step === 'otp' && (
              <form onSubmit={handleOtpSubmit} className="space-y-6 animate-fadeIn">
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
                    placeholder="000000"
                    className="h-14 text-center text-3xl tracking-widest font-mono"
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

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-blue-800">
                    <CheckCircle2 className="w-4 h-4" />
                    <p className="text-sm font-medium">
                      تسجيل الدخول لـ: <span className="font-bold">{formData.username}</span>
                    </p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <Button 
                    type="submit" 
                    className="w-full h-12 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.02] shadow-lg"
                    disabled={loading || !isOnline}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="ml-2 h-5 w-5 animate-spin" />
                        جاري التحقق...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="ml-2 h-5 w-5" />
                        تحقق من الرمز
                      </>
                    )}
                  </Button>

                  <Button 
                    type="button"
                    variant="outline"
                    className="w-full h-12"
                    onClick={handleBackToUsername}
                    disabled={loading}
                  >
                    إلغاء وتسجيل دخول مستخدم آخر
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
        
        <div className="mt-6 text-center space-y-2">
          {isOnline && (
            <div className="flex items-center justify-center gap-2 text-xs text-green-600">
              <Wifi className="w-3 h-3" />
              <span>متصل</span>
            </div>
          )}
          <p className="text-xs text-gray-500">
            © 2024 نظام الشكاوى الإلكتروني. جميع الحقوق محفوظة.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginEnhanced;
