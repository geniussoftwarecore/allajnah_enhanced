import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Loader2, Settings, AlertCircle, CheckCircle, User, Building2, 
  Shield, Check, X, Eye, EyeOff, ArrowRight, ArrowLeft, Sparkles,
  Mail, Phone, MapPin, Key, RefreshCw, Copy, Globe, Clock
} from 'lucide-react';
import { 
  validatePassword, getPasswordStrength, getStrengthLabel, 
  getStrengthColor, checkPasswordBreach, generateSecurePassword,
  getPasswordFeedback, estimateCrackTime
} from '@/lib/passwordValidation';
import { toast } from '@/lib/toast';

const SetupEnhanced = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState({
    // Step 1: Organization Info
    organization_name: '',
    organization_type: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Aden',
    locale: 'ar',
    
    // Step 2: Admin Account
    username: '',
    email: '',
    full_name: '',
    phone_number: '',
    address: '',
    
    // Step 3: Security
    password: '',
    confirmPassword: '',
    enable_2fa: false,
    
    // Step 4: Terms
    accept_terms: false,
    accept_privacy: false
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
  const [breachStatus, setBreachStatus] = useState({ checking: false, checked: false, breached: false });
  const [stepValidation, setStepValidation] = useState({});
  
  const navigate = useNavigate();

  const steps = [
    {
      id: 0,
      title: 'معلومات المنظمة',
      description: 'بيانات المؤسسة الأساسية',
      icon: Building2,
      fields: ['organization_name']
    },
    {
      id: 1,
      title: 'حساب المسؤول',
      description: 'إنشاء حساب المدير الأول',
      icon: User,
      fields: ['username', 'email', 'full_name']
    },
    {
      id: 2,
      title: 'الأمان',
      description: 'إعداد كلمة المرور والحماية',
      icon: Shield,
      fields: ['password', 'confirmPassword']
    },
    {
      id: 3,
      title: 'الشروط والأحكام',
      description: 'مراجعة والموافقة',
      icon: Check,
      fields: ['accept_terms', 'accept_privacy']
    }
  ];

  useEffect(() => {
    checkSetupStatus();
  }, []);

  useEffect(() => {
    if (formData.password) {
      const validation = validatePassword(formData.password);
      setPasswordValidation(validation);
      setPasswordStrength(getPasswordStrength(formData.password));
      
      if (validation.valid && formData.password.length >= 8) {
        checkBreach(formData.password);
      }
    } else {
      setPasswordValidation(null);
      setPasswordStrength(0);
      setBreachStatus({ checking: false, checked: false, breached: false });
    }
  }, [formData.password]);

  const checkSetupStatus = async () => {
    try {
      const response = await axios.get('/api/setup/status');
      setSetupRequired(response.data.setup_required);
      
      if (!response.data.setup_required) {
        toast.info('تم إعداد النظام مسبقاً');
        setTimeout(() => navigate('/login'), 2000);
      }
    } catch (err) {
      console.error('Setup status check failed:', err);
      toast.error('تعذر التحقق من حالة النظام');
      setSetupRequired(true);
    } finally {
      setCheckingSetup(false);
    }
  };

  const checkBreach = async (password) => {
    setBreachStatus({ checking: true, checked: false, breached: false });
    
    const result = await checkPasswordBreach(password);
    
    if (result.checked) {
      setBreachStatus({
        checking: false,
        checked: true,
        breached: result.breached,
        count: result.count
      });
      
      if (result.breached) {
        toast.warning(
          `تحذير: هذه الكلمة تم اختراقها ${result.count.toLocaleString('ar')} مرة في تسريبات البيانات`,
          { duration: 6000 }
        );
      }
    } else {
      setBreachStatus({ checking: false, checked: false, breached: false });
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
    setError('');
  };

  const validateStep = (step) => {
    const currentStepData = steps[step];
    const errors = [];

    switch (step) {
      case 0:
        if (!formData.organization_name || formData.organization_name.length < 3) {
          errors.push('اسم المنظمة يجب أن يكون 3 أحرف على الأقل');
        }
        break;

      case 1:
        if (!formData.username || formData.username.length < 3) {
          errors.push('اسم المستخدم يجب أن يكون 3 أحرف على الأقل');
        }
        if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
          errors.push('اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام فقط');
        }
        if (!formData.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
          errors.push('البريد الإلكتروني غير صالح');
        }
        if (!formData.full_name || formData.full_name.length < 3) {
          errors.push('الاسم الكامل مطلوب');
        }
        break;

      case 2:
        const passwordCheck = validatePassword(formData.password);
        if (!passwordCheck.valid) {
          errors.push(...passwordCheck.errors);
        }
        if (formData.password !== formData.confirmPassword) {
          errors.push('كلمة المرور وتأكيد كلمة المرور غير متطابقين');
        }
        if (breachStatus.breached) {
          errors.push('كلمة المرور هذه تم اختراقها. يرجى اختيار كلمة مرور أخرى');
        }
        break;

      case 3:
        if (!formData.accept_terms) {
          errors.push('يجب الموافقة على الشروط والأحكام');
        }
        if (!formData.accept_privacy) {
          errors.push('يجب الموافقة على سياسة الخصوصية');
        }
        break;
    }

    return errors;
  };

  const nextStep = () => {
    const errors = validateStep(currentStep);
    
    if (errors.length > 0) {
      setError(errors.join(' • '));
      toast.error(errors[0]);
      return;
    }
    
    setError('');
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
      toast.success('تم! انتقل للخطوة التالية');
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const errors = validateStep(currentStep);
    if (errors.length > 0) {
      setError(errors.join(' • '));
      toast.error(errors[0]);
      return;
    }

    setLoading(true);
    const toastId = toast.loading('جاري إنشاء حساب المسؤول...');

    try {
      const response = await axios.post('/api/setup/init', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        phone_number: formData.phone_number || undefined,
        address: formData.address || undefined,
        organization_name: formData.organization_name || undefined,
        timezone: formData.timezone,
        locale: formData.locale
      });

      toast.dismiss(toastId);
      toast.success('تم إنشاء الحساب بنجاح! 🎉', { duration: 5000 });
      setSuccess(true);
      
      setTimeout(() => navigate('/login'), 3000);
      
    } catch (err) {
      toast.dismiss(toastId);
      console.error('Setup error:', err);
      
      if (err.response?.data?.setup_already_complete) {
        toast.info('تم إعداد النظام بالفعل');
        setTimeout(() => navigate('/login'), 2000);
      } else {
        const errorMessage = err.response?.data?.message || 'خطأ في إنشاء حساب المسؤول';
        const errors = err.response?.data?.errors;
        
        if (errors) {
          const errorList = Object.values(errors).flat();
          setError(errorList.join(' • '));
          toast.error(errorList[0]);
        } else {
          setError(errorMessage);
          toast.error(errorMessage);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePassword = () => {
    const newPassword = generateSecurePassword(16);
    setFormData({
      ...formData,
      password: newPassword,
      confirmPassword: newPassword
    });
    setShowPassword(true);
    setShowConfirmPassword(true);
    toast.success('تم إنشاء كلمة مرور قوية!');
  };

  const handleCopyPassword = () => {
    navigator.clipboard.writeText(formData.password);
    toast.success('تم نسخ كلمة المرور!');
  };

  const PasswordRequirement = ({ met, text }) => (
    <div className={`flex items-center gap-2 text-xs transition-colors ${met ? 'text-green-600' : 'text-gray-500'}`}>
      {met ? (
        <div className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center">
          <Check className="w-3 h-3" />
        </div>
      ) : (
        <div className="w-4 h-4 rounded-full bg-gray-100 flex items-center justify-center">
          <X className="w-3 h-3" />
        </div>
      )}
      <span>{text}</span>
    </div>
  );

  if (checkingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">جاري التحقق من حالة النظام...</p>
        </div>
      </div>
    );
  }

  if (!setupRequired && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-sm max-w-md">
          <CardContent className="pt-6 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-12 h-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">تم إعداد النظام بالفعل</h2>
            <p className="text-gray-600 mb-4">جاري التحويل إلى صفحة تسجيل الدخول...</p>
            <div className="flex justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4">
        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-sm max-w-lg">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
              <Sparkles className="w-14 h-14 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-3">مرحباً بك! 🎉</h2>
            <p className="text-lg text-gray-700 mb-2">تم إنشاء حساب المسؤول بنجاح</p>
            <p className="text-sm text-gray-500 mb-6">جاري التحويل إلى صفحة تسجيل الدخول...</p>
            <div className="flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const StepIndicator = ({ step, currentStep }) => {
    const isCompleted = currentStep > step.id;
    const isCurrent = currentStep === step.id;
    const StepIcon = step.icon;

    return (
      <div className="flex flex-col items-center relative">
        <div
          className={`
            w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all duration-300 transform
            ${isCurrent ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white scale-110 shadow-lg' : ''}
            ${isCompleted ? 'bg-green-500 text-white' : ''}
            ${!isCurrent && !isCompleted ? 'bg-gray-200 text-gray-500' : ''}
          `}
        >
          {isCompleted ? (
            <Check className="w-6 h-6" />
          ) : (
            <StepIcon className="w-6 h-6" />
          )}
        </div>
        <p className={`text-xs text-center font-medium ${isCurrent ? 'text-blue-600' : 'text-gray-500'}`}>
          {step.title}
        </p>
      </div>
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4">
      <div className="w-full max-w-4xl">
        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center space-y-6 pb-6 border-b">
            <div className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-xl transform rotate-3">
              <Settings className="w-10 h-10 text-white transform -rotate-3" />
            </div>
            <div>
              <CardTitle className="text-3xl font-bold text-gray-900">
                إعداد النظام الأولي
              </CardTitle>
              <CardDescription className="text-gray-600 mt-2 text-lg">
                مرحباً! دعنا نقوم بإعداد نظام الشكاوى الإلكتروني
              </CardDescription>
            </div>

            {/* Step Indicators */}
            <div className="flex justify-between items-start max-w-2xl mx-auto pt-4">
              {steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <StepIndicator step={step} currentStep={currentStep} />
                  {index < steps.length - 1 && (
                    <div className={`flex-1 h-0.5 mt-6 mx-2 transition-colors ${currentStep > index ? 'bg-green-500' : 'bg-gray-300'}`} />
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Progress */}
            <div className="max-w-2xl mx-auto w-full">
              <Progress value={((currentStep + 1) / steps.length) * 100} className="h-2" />
              <p className="text-xs text-gray-500 mt-2 text-center">
                الخطوة {currentStep + 1} من {steps.length}
              </p>
            </div>
          </CardHeader>
          
          <CardContent className="p-8">
            <form onSubmit={currentStep === steps.length - 1 ? handleSubmit : (e) => { e.preventDefault(); nextStep(); }}>
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800">خطأ في البيانات</p>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {/* Step 0: Organization Info */}
              {currentStep === 0 && (
                <div className="space-y-6 animate-fadeIn">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-blue-600" />
                      معلومات المنظمة
                    </h3>
                    
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="organization_name" className="text-sm font-medium text-gray-700 mb-2 block">
                          اسم المنظمة / الجهة <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="organization_name"
                          name="organization_name"
                          type="text"
                          value={formData.organization_name}
                          onChange={handleChange}
                          placeholder="مثال: وزارة التجارة والصناعة"
                          className="h-12 text-right text-lg"
                          disabled={loading}
                          autoFocus
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1.5">سيظهر هذا الاسم في رأس النظام والتقارير</p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="timezone" className="text-sm font-medium text-gray-700 mb-2 block flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            المنطقة الزمنية
                          </Label>
                          <select
                            id="timezone"
                            name="timezone"
                            value={formData.timezone}
                            onChange={handleChange}
                            className="w-full h-12 px-3 text-right rounded-md border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            disabled={loading}
                          >
                            <option value="Asia/Aden">آسيا/عدن (GMT+3)</option>
                            <option value="Asia/Riyadh">آسيا/الرياض (GMT+3)</option>
                            <option value="Asia/Dubai">آسيا/دبي (GMT+4)</option>
                            <option value="Africa/Cairo">أفريقيا/القاهرة (GMT+2)</option>
                          </select>
                        </div>

                        <div>
                          <Label htmlFor="locale" className="text-sm font-medium text-gray-700 mb-2 block flex items-center gap-2">
                            <Globe className="w-4 h-4" />
                            اللغة الافتراضية
                          </Label>
                          <select
                            id="locale"
                            name="locale"
                            value={formData.locale}
                            onChange={handleChange}
                            className="w-full h-12 px-3 text-right rounded-md border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            disabled={loading}
                          >
                            <option value="ar">العربية</option>
                            <option value="en">English</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 1: Admin Account */}
              {currentStep === 1 && (
                <div className="space-y-6 animate-fadeIn">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <User className="w-5 h-5 text-blue-600" />
                    حساب المسؤول الأول
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="username" className="text-sm font-medium text-gray-700 mb-2 block">
                        اسم المستخدم <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="username"
                        name="username"
                        type="text"
                        value={formData.username}
                        onChange={handleChange}
                        placeholder="admin"
                        className="h-12 text-right"
                        disabled={loading}
                        autoFocus
                        required
                        dir="ltr"
                      />
                      <p className="text-xs text-gray-500 mt-1.5">أحرف إنجليزية وأرقام فقط (بدون مسافات)</p>
                    </div>

                    <div>
                      <Label htmlFor="email" className="text-sm font-medium text-gray-700 mb-2 block flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        البريد الإلكتروني <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="email"
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleChange}
                        placeholder="admin@example.com"
                        className="h-12 text-right"
                        disabled={loading}
                        required
                        dir="ltr"
                      />
                    </div>

                    <div className="md:col-span-2">
                      <Label htmlFor="full_name" className="text-sm font-medium text-gray-700 mb-2 block">
                        الاسم الكامل <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="full_name"
                        name="full_name"
                        type="text"
                        value={formData.full_name}
                        onChange={handleChange}
                        placeholder="أدخل الاسم الكامل"
                        className="h-12 text-right"
                        disabled={loading}
                        required
                      />
                    </div>

                    <div>
                      <Label htmlFor="phone_number" className="text-sm font-medium text-gray-700 mb-2 block flex items-center gap-2">
                        <Phone className="w-4 h-4" />
                        رقم الهاتف
                      </Label>
                      <Input
                        id="phone_number"
                        name="phone_number"
                        type="tel"
                        value={formData.phone_number}
                        onChange={handleChange}
                        placeholder="+967 xxx xxx xxx"
                        className="h-12 text-right"
                        disabled={loading}
                      />
                    </div>

                    <div>
                      <Label htmlFor="address" className="text-sm font-medium text-gray-700 mb-2 block flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        العنوان
                      </Label>
                      <Input
                        id="address"
                        name="address"
                        type="text"
                        value={formData.address}
                        onChange={handleChange}
                        placeholder="المدينة، الدولة"
                        className="h-12 text-right"
                        disabled={loading}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Security */}
              {currentStep === 2 && (
                <div className="space-y-6 animate-fadeIn">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                      <Key className="w-5 h-5 text-blue-600" />
                      إعداد كلمة المرور
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleGeneratePassword}
                      disabled={loading}
                      className="gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      إنشاء تلقائياً
                    </Button>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="password" className="text-sm font-medium text-gray-700 mb-2 block">
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
                          className="h-12 text-right pr-20"
                          disabled={loading}
                          required
                          dir="ltr"
                          autoFocus
                        />
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 flex gap-1">
                          {formData.password && (
                            <button
                              type="button"
                              onClick={handleCopyPassword}
                              className="text-gray-500 hover:text-gray-700 p-1"
                              title="نسخ"
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="text-gray-500 hover:text-gray-700 p-1"
                          >
                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700 mb-2 block">
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
                          className="h-12 text-right pr-10"
                          disabled={loading}
                          required
                          dir="ltr"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                        >
                          {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Password Strength */}
                  {formData.password && passwordValidation && (
                    <div className="space-y-4">
                      <div className="p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border border-gray-200">
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-sm font-medium text-gray-700">قوة كلمة المرور</span>
                          <span className={`text-sm font-bold ${passwordStrength >= 4 ? 'text-green-600' : passwordStrength >= 3 ? 'text-yellow-600' : 'text-red-600'}`}>
                            {getStrengthLabel(passwordStrength)}
                          </span>
                        </div>
                        <div className="flex gap-1 mb-3">
                          {[1, 2, 3, 4, 5].map((level) => (
                            <div
                              key={level}
                              className={`h-2 flex-1 rounded-full transition-all ${
                                level <= passwordStrength ? getStrengthColor(passwordStrength) : 'bg-gray-300'
                              }`}
                            />
                          ))}
                        </div>
                        <p className="text-xs text-gray-600">
                          وقت الاختراق المقدر: <span className="font-semibold">{estimateCrackTime(formData.password)}</span>
                        </p>
                      </div>

                      {/* Breach Check Status */}
                      {breachStatus.checking && (
                        <div className="flex items-center gap-2 text-sm text-gray-600 p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>جاري التحقق من قاعدة بيانات الاختراقات...</span>
                        </div>
                      )}
                      
                      {breachStatus.checked && breachStatus.breached && (
                        <div className="flex items-start gap-2 text-sm text-red-700 p-3 bg-red-50 rounded-lg border border-red-200">
                          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="font-semibold">تحذير أمني!</p>
                            <p>تم العثور على هذه الكلمة في {breachStatus.count?.toLocaleString('ar')} تسريب بيانات. يرجى اختيار كلمة مرور أخرى.</p>
                          </div>
                        </div>
                      )}
                      
                      {breachStatus.checked && !breachStatus.breached && (
                        <div className="flex items-center gap-2 text-sm text-green-700 p-3 bg-green-50 rounded-lg border border-green-200">
                          <CheckCircle className="w-4 h-4" />
                          <span>ممتاز! لم يتم العثور على هذه الكلمة في تسريبات البيانات</span>
                        </div>
                      )}

                      {/* Password Requirements */}
                      <div className="p-4 bg-white rounded-lg border border-gray-200">
                        <p className="text-sm font-semibold text-gray-700 mb-3">متطلبات كلمة المرور:</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <PasswordRequirement met={passwordValidation.checks.length} text="8 أحرف على الأقل" />
                          <PasswordRequirement met={passwordValidation.checks.uppercase} text="حرف كبير (A-Z)" />
                          <PasswordRequirement met={passwordValidation.checks.lowercase} text="حرف صغير (a-z)" />
                          <PasswordRequirement met={passwordValidation.checks.number} text="رقم (0-9)" />
                          <PasswordRequirement met={passwordValidation.checks.special} text="رمز خاص (!@#$%)" />
                          <PasswordRequirement met={passwordValidation.checks.notCommon} text="ليست شائعة" />
                          <PasswordRequirement met={passwordValidation.checks.noSequential} text="لا تحتوي تسلسل" />
                          <PasswordRequirement met={passwordValidation.checks.noRepeated} text="لا أحرف متكررة" />
                        </div>
                      </div>

                      {/* Password Feedback */}
                      {getPasswordFeedback(formData.password).map((feedback, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm text-blue-700 p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <span>{feedback}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: Terms */}
              {currentStep === 3 && (
                <div className="space-y-6 animate-fadeIn">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">الشروط والأحكام</h3>
                  
                  <div className="space-y-4">
                    <div className="p-6 bg-gray-50 rounded-lg border border-gray-200 max-h-64 overflow-y-auto">
                      <h4 className="font-semibold text-gray-900 mb-3">شروط استخدام نظام الشكاوى الإلكتروني</h4>
                      <div className="space-y-2 text-sm text-gray-700">
                        <p>1. هذا النظام مخصص لإدارة الشكاوى بشكل احترافي وآمن.</p>
                        <p>2. يجب الحفاظ على سرية بيانات الدخول وعدم مشاركتها مع أي طرف ثالث.</p>
                        <p>3. يتحمل المستخدم مسؤولية جميع الإجراءات التي تتم من خلال حسابه.</p>
                        <p>4. يجب استخدام النظام بما يتوافق مع القوانين واللوائح المعمول بها.</p>
                        <p>5. تحتفظ الإدارة بالحق في تعليق أو إلغاء أي حساب في حالة إساءة الاستخدام.</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <Checkbox
                          id="accept_terms"
                          name="accept_terms"
                          checked={formData.accept_terms}
                          onCheckedChange={(checked) => 
                            setFormData({ ...formData, accept_terms: checked })
                          }
                          disabled={loading}
                          className="mt-1"
                        />
                        <Label htmlFor="accept_terms" className="text-sm font-medium text-gray-700 cursor-pointer flex-1">
                          أوافق على الشروط والأحكام المذكورة أعلاه <span className="text-red-500">*</span>
                        </Label>
                      </div>

                      <div className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <Checkbox
                          id="accept_privacy"
                          name="accept_privacy"
                          checked={formData.accept_privacy}
                          onCheckedChange={(checked) => 
                            setFormData({ ...formData, accept_privacy: checked })
                          }
                          disabled={loading}
                          className="mt-1"
                        />
                        <Label htmlFor="accept_privacy" className="text-sm font-medium text-gray-700 cursor-pointer flex-1">
                          أوافق على سياسة الخصوصية وأتعهد بحماية بيانات المستخدمين <span className="text-red-500">*</span>
                        </Label>
                      </div>
                    </div>

                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm text-blue-800">
                        📝 بقبولك لهذه الشروط، فإنك تتعهد بإدارة النظام بمسؤولية والحفاظ على سرية وأمان البيانات.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex justify-between gap-4 mt-8 pt-6 border-t">
                {currentStep > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={prevStep}
                    disabled={loading}
                    className="gap-2 h-12 px-6"
                  >
                    <ArrowRight className="w-4 h-4" />
                    السابق
                  </Button>
                )}
                
                <div className="flex-1" />
                
                {currentStep < steps.length - 1 ? (
                  <Button
                    type="submit"
                    className="gap-2 h-12 px-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                    disabled={loading}
                  >
                    التالي
                    <ArrowLeft className="w-4 h-4" />
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    className="gap-2 h-12 px-8 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                    disabled={loading || !formData.accept_terms || !formData.accept_privacy}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        جاري الإنشاء...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        إتمام الإعداد
                      </>
                    )}
                  </Button>
                )}
              </div>
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

export default SetupEnhanced;
