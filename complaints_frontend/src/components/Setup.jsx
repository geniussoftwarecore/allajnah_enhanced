import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Settings, AlertCircle, CheckCircle, XCircle, Check, X } from 'lucide-react';

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
  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false
  });
  
  const navigate = useNavigate();

  useEffect(() => {
    checkSetupStatus();
  }, []);

  useEffect(() => {
    validatePassword(formData.password);
  }, [formData.password]);

  const checkSetupStatus = async () => {
    try {
      const response = await axios.get('/api/setup/status');
      setSetupRequired(response.data.setup_required);
      
      if (!response.data.setup_required) {
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }
    } catch (err) {
      setError('خطأ في التحقق من حالة الإعداد');
    } finally {
      setCheckingSetup(false);
    }
  };

  const validatePassword = (password) => {
    setPasswordValidation({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*()_+\-=\[\]{};:'",.<>?/\\|`~]/.test(password)
    });
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

    // Validation checks
    if (!formData.username || !formData.email || !formData.password || !formData.full_name) {
      setError('يرجى إدخال جميع الحقول المطلوبة');
      setLoading(false);
      return;
    }

    // Username validation
    if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      setError('اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام و _ و - فقط (لا أحرف عربية)');
      setLoading(false);
      return;
    }

    if (formData.username.length < 3) {
      setError('اسم المستخدم يجب أن يكون 3 أحرف على الأقل');
      setLoading(false);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('كلمة المرور وتأكيد كلمة المرور غير متطابقين');
      setLoading(false);
      return;
    }

    // Check all password requirements
    const allRequirementsMet = Object.values(passwordValidation).every(val => val === true);
    if (!allRequirementsMet) {
      setError('يرجى التأكد من استيفاء جميع متطلبات كلمة المرور');
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
      if (err.response?.data?.setup_already_complete) {
        setError('تم إعداد النظام بالفعل. جاري التحويل إلى صفحة تسجيل الدخول...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        const errorMessage = err.response?.data?.message || 'خطأ في إنشاء حساب المسؤول';
        const errors = err.response?.data?.errors;
        
        if (errors) {
          const errorList = Object.values(errors).flat().join(' - ');
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
    <div className={`flex items-center gap-2 text-sm ${met ? 'text-green-600' : 'text-gray-500'}`}>
      {met ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
      <span>{text}</span>
    </div>
  );

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

  if (!setupRequired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm max-w-md">
          <CardContent className="pt-6 text-center">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">تم إعداد النظام بالفعل</h2>
            <p className="text-gray-600 mb-4">جاري التحويل إلى صفحة تسجيل الدخول...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm max-w-md">
          <CardContent className="pt-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">تم إنشاء الحساب بنجاح!</h2>
            <p className="text-gray-600 mb-4">جاري التحويل إلى صفحة تسجيل الدخول...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
              <Settings className="w-8 h-8 text-white" />
            </div>
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                إعداد النظام الأولي
              </CardTitle>
              <CardDescription className="text-gray-600 mt-2">
                قم بإنشاء حساب المسؤول الأول للنظام (اللجنة العليا)
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive" className="border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-800">
                    {error}
                  </AlertDescription>
                </Alert>
              )}
              
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
                    placeholder="أدخل اسم المستخدم (بالإنجليزية فقط)"
                    className="h-11 text-right"
                    disabled={loading}
                    required
                  />
                  <p className="text-xs text-gray-500">أحرف إنجليزية وأرقام و _ و - فقط</p>
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
                    placeholder="أدخل البريد الإلكتروني"
                    className="h-11 text-right"
                    disabled={loading}
                    required
                  />
                </div>

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
                    placeholder="أدخل رقم الهاتف (اختياري)"
                    className="h-11 text-right"
                    disabled={loading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                    كلمة المرور <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="أدخل كلمة المرور"
                    className="h-11 text-right"
                    disabled={loading}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700">
                    تأكيد كلمة المرور <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder="أعد إدخال كلمة المرور"
                    className="h-11 text-right"
                    disabled={loading}
                    required
                  />
                </div>
              </div>

              {/* Password Requirements */}
              {formData.password && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
                  <p className="text-sm font-medium text-gray-700 mb-3">متطلبات كلمة المرور:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <PasswordRequirement met={passwordValidation.length} text="8 أحرف على الأقل" />
                    <PasswordRequirement met={passwordValidation.uppercase} text="حرف كبير واحد على الأقل (A-Z)" />
                    <PasswordRequirement met={passwordValidation.lowercase} text="حرف صغير واحد على الأقل (a-z)" />
                    <PasswordRequirement met={passwordValidation.number} text="رقم واحد على الأقل (0-9)" />
                    <PasswordRequirement met={passwordValidation.special} text="رمز خاص واحد على الأقل (!@#$%)" />
                  </div>
                </div>
              )}

              <div className="space-y-2">
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
              
              <Button 
                type="submit" 
                className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium transition-all duration-200 transform hover:scale-[1.02]"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    جاري إنشاء الحساب...
                  </>
                ) : (
                  'إنشاء حساب المسؤول'
                )}
              </Button>
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

export default Setup;
