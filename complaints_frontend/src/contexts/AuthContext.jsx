import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check if user is logged in on app start
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get('/api/profile');
          setUser(response.data.user);
        } catch (error) {
          console.error('Auth check failed:', error);
          
          // Only logout if it's an authentication error (401/403)
          // Don't logout on network errors or server errors
          if (error.response && (error.response.status === 401 || error.response.status === 403)) {
            logout();
          } else {
            // Keep the session but log the error
            console.warn('Profile fetch failed but keeping session:', error.message);
          }
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  /**
   * Login with optional OTP support
   * @param {string} username - Username
   * @param {string} password - Password  
   * @param {string} otpCode - Optional OTP code for 2FA
   * @returns {object} Result object with success, otpRequired, message, etc.
   */
  const login = async (username, password, otpCode = null) => {
    try {
      const payload = {
        username,
        password
      };

      // Include OTP code if provided
      if (otpCode) {
        payload.otp_code = otpCode;
      }

      const response = await axios.post('/api/login', payload);

      // Check if 2FA/OTP is required
      if (response.data.requires_2fa) {
        return {
          success: false,
          otpRequired: true,
          message: response.data.message || 'يرجى إدخال رمز التحقق (OTP) من تطبيق المصادقة'
        };
      }

      // Successful login - use access_token and refresh_token from backend
      const { access_token, refresh_token, user: userData } = response.data;
      const newToken = access_token;
      
      setToken(newToken);
      setUser(userData);
      localStorage.setItem('token', newToken);
      
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      
      // Extract detailed error message
      let message = 'فشل في تسجيل الدخول';
      
      if (error.response) {
        const { status, data } = error.response;
        
        // Specific error messages based on status code
        if (status === 401) {
          message = data.message || 'اسم المستخدم أو كلمة المرور غير صحيحة';
        } else if (status === 403) {
          message = data.message || 'تم قفل الحساب أو غير مصرح بالدخول';
        } else if (status === 429) {
          message = 'تم تجاوز عدد محاولات تسجيل الدخول. يرجى المحاولة لاحقاً';
        } else if (status === 400) {
          message = data.message || 'بيانات تسجيل الدخول غير صحيحة';
        } else if (status >= 500) {
          message = 'خطأ في الخادم. يرجى المحاولة لاحقاً';
        } else {
          message = data.message || message;
        }
      } else if (error.request) {
        // Network error - no response received
        message = 'خطأ في الاتصال بالخادم. يرجى التحقق من اتصال الإنترنت';
      }
      
      return { 
        success: false,
        otpRequired: false,
        message
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await axios.put('/api/profile', profileData);
      setUser(response.data.user);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Profile update failed:', error);
      
      let message = 'فشل في تحديث الملف الشخصي';
      if (error.response?.data?.message) {
        message = error.response.data.message;
      } else if (error.response?.data?.errors) {
        const errors = Object.values(error.response.data.errors).flat();
        message = errors.join(' • ');
      }
      
      return { 
        success: false, 
        message
      };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      const response = await axios.post('/api/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Password change failed:', error);
      
      let message = 'فشل في تغيير كلمة المرور';
      if (error.response?.data?.message) {
        message = error.response.data.message;
      } else if (error.response?.data?.errors) {
        const errors = Object.values(error.response.data.errors).flat();
        message = errors.join(' • ');
      }
      
      return { 
        success: false, 
        message
      };
    }
  };

  /**
   * Refresh user profile from server
   */
  const refreshProfile = async () => {
    if (!token) return { success: false, message: 'لم يتم تسجيل الدخول' };
    
    try {
      const response = await axios.get('/api/profile');
      setUser(response.data.user);
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Profile refresh failed:', error);
      
      // Only logout on auth errors
      if (error.response && (error.response.status === 401 || error.response.status === 403)) {
        logout();
      }
      
      return { 
        success: false, 
        message: error.response?.data?.message || 'فشل في تحديث البيانات'
      };
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    updateProfile,
    changePassword,
    refreshProfile,
    isAuthenticated: !!token && !!user,
    isTrader: user?.role_name === 'Trader',
    isTechnicalCommittee: user?.role_name === 'Technical Committee',
    isHigherCommittee: user?.role_name === 'Higher Committee'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
