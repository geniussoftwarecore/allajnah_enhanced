import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Loader2, Settings, AlertCircle, CheckCircle, XCircle, Check, X, Eye, EyeOff } from 'lucide-react';
import { validatePassword, getPasswordStrength, getStrengthLabel, getStrengthColor } from '@/lib/passwordValidation';

const Setup = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    phone_number: '',
    address: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordValidation, setPasswordValidation] = useState(null);
  const [passwordStrength, setPasswordStrength] = useState(0);
  
  const navigate = useNavigate();

  useEffect(() => {
    checkSetupStatus();
  }, []);

  useEffect(() => {
    if (formData.password) {
      const validation = validatePassword(formData.password);
      setPasswordValidation(validation);
      setPasswordStrength(getPasswordStrength(formData.password));
    } else {
      setPasswordValidation(null);
      setPasswordStrength(0);
    }
  }, [formData.password]);

  const checkSetupStatus = async () => {
    try {
      const response = await axios.get('/api/setup/status');
      setSetupRequired(response.data.setup_required);
      
      if (!response.data.setup_required) {
        // System already set up - redirect after a delay
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }
    } catch (err) {
      // If we can't check setup status, show error but allow user to try setup
      console.error('Setup status check failed:', err);
      setError('تعذر التحقق من حالة النظام. يرجى التحقق من اتصال الخادم.');
      setSetupRequired(true); // Allow them to try
    } finally {
      setCheckingSetup(false);
    }
  };

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

    // Basic validation
    if (!formData.username || !formData.email || !formData.password || !formData.full_name) {
      setError('يرجى إدخال جميع الحقول المطلوبة (مميزة بـ *)');
      setLoading(false);
      return;
    }

    // Username validation
    if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      setError('اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام و _ و - فقط');
      setLoading(false);
      return;
    }

    if (formData.username.length < 3) {
      setError('اسم المستخدم يجب أن يكون 3 أحرف على الأقل');
      setLoading(false);
      return;
    }

    // Password validation
    const passwordCheck = validatePassword(formData.password);
    if (!passwordCheck.valid) {
      setError('كلمة المرور لا تستوفي المتطلبات:\n' + passwordCheck.errors.join('\n'));
      setLoading(false);
      return;
    }

    // Confirm password
    if (formData.password !== formData.confirmPassword) {
      setError('كلمة المرور وتأكيد كلمة المرور غير متطابقين');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post('/api/setup/init', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        phone_number: formData.phone_number || undefined,
        address: formData.address || undefined
      });

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3000);
      
    } catch (err) {
      console.error('Setup error:', err);
      
      if (err.response?.data?.setup_already_complete) {
        setError('تم إعداد النظام بالفعل. جاري التحويل إلى صفحة تسجيل الدخول...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        // Extract error message
        const errorMessage = err.response?.data?.message || 'خطأ في إنشاء حساب المسؤول';
        const errors = err.response?.data?.errors;
        
        if (errors) {
          const errorList = Object.values(errors).flat().join(' • ');
          setError(`${errorMessage}: ${errorList}`);
        } else {
          setError(errorMessage);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const PasswordRequirement = ({ met, text }) => (
    <div className={`flex items-center gap-2 text-xs ${met ? 'text-green-600' : 'text-gray-500'}`}>
      {met ? <Check className="w-3.5 h-3.5 flex-shrink-0" /> : <X className="w-3.5 h-3.5 flex-shrink-0" />}
      <span>{text}</span>
    </div>
  );

  // Loading state
  if (checkingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">جاري التحقق من حالة النظام...</p>
        </div>
      </div>
    );
  }

  // Already set up
  if (!setupRequired && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm max-w-md">
          <CardContent className="pt-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">تم إعداد النظام بالفعل</h2>
            <p className="text-gray-600 mb-4">جاري التحويل إلى صفحة تسجيل الدخول...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm max-w-md">
          <CardContent className="pt-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">تم إنشاء الحساب بنجاح!</h2>
            <p className="text-gray-600 mb-2">تم إنشاء حساب المسؤول الأول بنجاح</p>
            <p className="text-sm text-gray-500">جاري التحويل إلى صفحة تسجيل الدخول...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Setup form
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-3xl">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center space-y-4 pb-6">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
              <Settings className="w-8 h-8 text-white" />
            </div>
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                إعداد النظام الأولي
              </CardTitle>
              <CardDescription className="text-gray-600 mt-2">
                قم بإنشاء حساب المسؤول الأول للنظام
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <Alert variant="destructive" className="border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-800 whitespace-pre-line">
                    {error}
                  </AlertDescription>
                </Alert>
              )}
              
              {/* Account Information Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 border-b pb-2">معلومات الحساب</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-sm font-medium text-gray-700">
                      اسم المستخدم <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      value={formData.username}
                      onChange={handleChange}
                      placeholder="admin"
                      className="h-11 text-right"
                      disabled={loading}
                      required
                      dir="ltr"
                    />
                    <p className="text-xs text-gray-500">أحرف إنجليزية وأرقام و _ و - فقط (لا مسافات)</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                      البريد الإلكتروني <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="admin@example.com"
                      className="h-11 text-right"
                      disabled={loading}
                      required
                      dir="ltr"
                    />
                  </div>
                </div>
              </div>

              {/* Personal Information Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 border-b pb-2">المعلومات الشخصية</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full_name" className="text-sm font-medium text-gray-700">
                      الاسم الكامل <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="full_name"
                      name="full_name"
                      type="text"
                      value={formData.full_name}
                      onChange={handleChange}
                      placeholder="أدخل الاسم الكامل"
                      className="h-11 text-right"
                      disabled={loading}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone_number" className="text-sm font-medium text-gray-700">
                      رقم الهاتف
                    </Label>
                    <Input
                      id="phone_number"
                      name="phone_number"
                      type="tel"
                      value={formData.phone_number}
                      onChange={handleChange}
                      placeholder="+967 xxx xxx xxx"
                      className="h-11 text-right"
                      disabled={loading}
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="address" className="text-sm font-medium text-gray-700">
                      العنوان
                    </Label>
                    <Input
                      id="address"
                      name="address"
                      type="text"
                      value={formData.address}
                      onChange={handleChange}
                      placeholder="أدخل العنوان (اختياري)"
                      className="h-11 text-right"
                      disabled={loading}
                    />
                  </div>
                </div>
              </div>

              {/* Password Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 border-b pb-2">كلمة المرور</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                      كلمة المرور <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        name="password"
                        type={showPassword ? "text" : "password"}
                        value={formData.password}
                        onChange={handleChange}
                        placeholder="أدخل كلمة مرور قوية"
                        className="h-11 text-right pr-10"
                        disabled={loading}
                        required
                        dir="ltr"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700">
                      تأكيد كلمة المرور <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        placeholder="أعد إدخال كلمة المرور"
                        className="h-11 text-right pr-10"
                        disabled={loading}
                        required
                        dir="ltr"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Password Strength Meter */}
                {formData.password && (
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-gray-600">قوة كلمة المرور:</span>
                        <span className="font-medium">{getStrengthLabel(passwordStrength)}</span>
                      </div>
                      <Progress value={passwordStrength} className="h-2" />
                    </div>

                    {passwordValidation && (
                      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
                        <p className="text-xs font-medium text-gray-700 mb-2">متطلبات كلمة المرور:</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          <PasswordRequirement met={passwordValidation.checks.length} text="8 أحرف على الأقل" />
                          <PasswordRequirement met={passwordValidation.checks.uppercase} text="حرف كبير (A-Z)" />
                          <PasswordRequirement met={passwordValidation.checks.lowercase} text="حرف صغير (a-z)" />
                          <PasswordRequirement met={passwordValidation.checks.number} text="رقم واحد (0-9)" />
                          <PasswordRequirement met={passwordValidation.checks.special} text="رمز خاص (!@#$%)" />
                          <PasswordRequirement met={passwordValidation.checks.notCommon} text="ليست كلمة شائعة" />
                          <PasswordRequirement met={passwordValidation.checks.noSequential} text="لا تحتوي تسلسلات" />
                          <PasswordRequirement met={passwordValidation.checks.noRepeated} text="لا أحرف متكررة" />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="pt-2">
                <Button 
                  type="submit" 
                  className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.01]"
                  disabled={loading || (passwordValidation && !passwordValidation.valid)}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      جاري إنشاء الحساب...
                    </>
                  ) : (
                    'إنشاء حساب المسؤول'
                  )}
                </Button>
              </div>

              <p className="text-xs text-center text-gray-500">
                * الحقول المميزة بهذه العلامة مطلوبة
              </p>
            </form>
          </CardContent>
        </Card>
        
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            © 2024 نظام الشكاوى الإلكتروني. جميع الحقوق محفوظة.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Setup;
