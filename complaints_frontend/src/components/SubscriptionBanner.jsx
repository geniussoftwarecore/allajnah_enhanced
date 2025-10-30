import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export const SubscriptionBanner = ({ userId }) => {
  const [subscription, setSubscription] = useState(null);
  const [daysRemaining, setDaysRemaining] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (userId) {
      fetchSubscriptionStatus();
      const interval = setInterval(calculateDaysRemaining, 60000);
      return () => clearInterval(interval);
    }
  }, [userId]);

  const fetchSubscriptionStatus = async () => {
    try {
      const response = await axios.get(`/api/subscriptions/user/${userId}/status`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      setSubscription(response.data);
      calculateDaysRemaining(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
      setLoading(false);
    }
  };

  const calculateDaysRemaining = (subData = subscription) => {
    if (!subData || !subData.end_date) return;
    
    const endDate = new Date(subData.end_date);
    const now = new Date();
    const diffTime = endDate - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    setDaysRemaining(diffDays);
  };

  if (loading || !subscription) return null;

  const getAlertVariant = () => {
    if (subscription.status === 'expired') return 'destructive';
    if (daysRemaining <= 7) return 'destructive';
    if (daysRemaining <= 14) return 'warning';
    return 'default';
  };

  const getIcon = () => {
    if (subscription.status === 'expired') return <XCircle className="h-5 w-5" />;
    if (daysRemaining <= 7) return <AlertTriangle className="h-5 w-5" />;
    if (daysRemaining <= 14) return <Clock className="h-5 w-5" />;
    return <CheckCircle className="h-5 w-5" />;
  };

  const getMessage = () => {
    if (subscription.status === 'expired') {
      if (subscription.grace_period_enabled) {
        return 'انتهى اشتراكك. أنت الآن في فترة السماح (7 أيام) - يرجى التجديد في أقرب وقت.';
      }
      return 'انتهى اشتراكك. يرجى تجديد الاشتراك للاستمرار في استخدام النظام.';
    }
    
    if (daysRemaining <= 0) return 'ينتهي اشتراكك اليوم! يرجى التجديد فوراً.';
    if (daysRemaining === 1) return 'تبقى يوم واحد على انتهاء اشتراكك.';
    if (daysRemaining <= 7) return `تبقى ${daysRemaining} أيام على انتهاء اشتراكك.`;
    if (daysRemaining <= 14) return `تبقى ${daysRemaining} يوماً على انتهاء اشتراكك.`;
    return `اشتراكك نشط - ينتهي بعد ${daysRemaining} يوماً.`;
  };

  if (subscription.status === 'active' && daysRemaining > 30) {
    return null;
  }

  return (
    <div className="w-full px-4 py-2">
      <Alert variant={getAlertVariant()} className="border-r-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1">
            {getIcon()}
            <AlertDescription className="text-sm font-medium">
              {getMessage()}
            </AlertDescription>
          </div>
          {subscription.status !== 'active' && (
            <Button 
              size="sm" 
              onClick={() => navigate('/payment')}
              className="shrink-0"
            >
              تجديد الاشتراك
            </Button>
          )}
        </div>
      </Alert>
    </div>
  );
};

export default SubscriptionBanner;
