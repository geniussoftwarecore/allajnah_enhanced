import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Shield, ShieldCheck, ShieldAlert, RefreshCw, QrCode, Key, Lock } from 'lucide-react';
import { toast } from '@/lib/toast';

export const SecurityDashboard = ({ user }) => {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [show2FADialog, setShow2FADialog] = useState(false);
  const [qrCode, setQrCode] = useState(null);
  const [secret, setSecret] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSecurityData();
  }, []);

  const fetchSecurityData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [statsRes, eventsRes] = await Promise.all([
        axios.get('/api/security/stats', { headers }),
        axios.get('/api/security/security-events', { headers })
      ]);

      setStats(statsRes.data);
      setEvents(eventsRes.data.events || []);
    } catch (error) {
      toast.error('فشل تحميل بيانات الأمان');
      console.error('Security error:', error);
    } finally {
      setLoading(false);
    }
  };

  const setup2FA = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('/api/security/2fa/setup', {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      setQrCode(response.data.qr_code);
      setSecret(response.data.secret);
      setShow2FADialog(true);
    } catch (error) {
      toast.error('فشل إعداد المصادقة الثنائية');
      console.error('2FA setup error:', error);
    }
  };

  const enable2FA = async () => {
    try {
      if (!verificationCode || verificationCode.length !== 6) {
        toast.error('يرجى إدخال رمز التحقق المكون من 6 أرقام');
        return;
      }

      const token = localStorage.getItem('token');
      await axios.post('/api/security/2fa/enable', {
        secret,
        code: verificationCode
      }, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      toast.success('تم تفعيل المصادقة الثنائية بنجاح');
      setShow2FADialog(false);
      setVerificationCode('');
      fetchSecurityData();
    } catch (error) {
      toast.error(error.response?.data?.error || 'فشل تفعيل المصادقة الثنائية');
    }
  };

  const getEventIcon = (actionType) => {
    if (actionType.includes('2fa')) return <Shield className="h-4 w-4 text-blue-500" />;
    if (actionType.includes('password')) return <Key className="h-4 w-4 text-yellow-500" />;
    if (actionType.includes('login')) return <Lock className="h-4 w-4 text-green-500" />;
    return <ShieldAlert className="h-4 w-4 text-gray-500" />;
  };

  const getEventBadgeColor = (actionType) => {
    if (actionType.includes('failed') || actionType.includes('locked')) return 'destructive';
    if (actionType.includes('enabled') || actionType.includes('success')) return 'success';
    return 'default';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">لوحة الأمان</h1>
          <p className="text-gray-500 mt-1">إدارة إعدادات الأمان ومراقبة الأحداث</p>
        </div>
        <Button onClick={fetchSecurityData} variant="outline" size="icon">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-green-500" />
                المستخدمون مع 2FA
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.users_with_2fa}</div>
              <p className="text-xs text-gray-500 mt-1">
                معدل التبني: {stats['2fa_adoption_rate']}%
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">عمليات الدخول</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_logins}</div>
              <p className="text-xs text-gray-500 mt-1">
                فشل: {stats.failed_logins}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">تغييرات كلمة المرور</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.password_changes}</div>
              <p className="text-xs text-gray-500 mt-1">آخر 30 يوم</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>المصادقة الثنائية (2FA)</CardTitle>
              <CardDescription>تأمين حسابك بطبقة حماية إضافية</CardDescription>
            </div>
            {!user?.two_factor_enabled ? (
              <Button onClick={setup2FA}>
                <QrCode className="h-4 w-4 ml-2" />
                تفعيل 2FA
              </Button>
            ) : (
              <Badge variant="success" className="gap-2">
                <ShieldCheck className="h-4 w-4" />
                مفعلة
              </Badge>
            )}
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>الأحداث الأمنية الأخيرة</CardTitle>
          <CardDescription>سجل الأنشطة الأمنية للنظام</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>النوع</TableHead>
                  <TableHead>المستخدم</TableHead>
                  <TableHead>التفاصيل</TableHead>
                  <TableHead>التوقيت</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-gray-500 py-8">
                      لا توجد أحداث
                    </TableCell>
                  </TableRow>
                ) : (
                  events.map((event) => (
                    <TableRow key={event.log_id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getEventIcon(event.action_type)}
                          <Badge variant={getEventBadgeColor(event.action_type)}>
                            {event.action_type}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>{event.performed_by_name || 'غير محدد'}</TableCell>
                      <TableCell className="max-w-md truncate">{event.details || '-'}</TableCell>
                      <TableCell>
                        {event.timestamp ? new Date(event.timestamp).toLocaleString('ar-YE') : '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={show2FADialog} onOpenChange={setShow2FADialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>تفعيل المصادقة الثنائية</DialogTitle>
            <DialogDescription>
              امسح رمز QR باستخدام تطبيق المصادقة (Google Authenticator أو Authy)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {qrCode && (
              <div className="flex flex-col items-center gap-4">
                <img src={qrCode} alt="QR Code" className="w-48 h-48" />
                <div className="text-center">
                  <p className="text-sm text-gray-500 mb-2">أو أدخل الرمز يدوياً:</p>
                  <code className="bg-gray-100 px-3 py-1 rounded text-sm">{secret}</code>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="verification-code">رمز التحقق</Label>
              <Input
                id="verification-code"
                placeholder="أدخل الرمز المكون من 6 أرقام"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                maxLength={6}
              />
            </div>
            <Button onClick={enable2FA} className="w-full">
              تأكيد وتفعيل
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SecurityDashboard;
