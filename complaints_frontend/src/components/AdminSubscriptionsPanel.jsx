import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  Calendar, 
  Search, 
  RefreshCw, 
  UserCheck, 
  UserX, 
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react';
import { toast } from '@/lib/toast';

export const AdminSubscriptionsPanel = () => {
  const [subscriptions, setSubscriptions] = useState([]);
  const [filteredSubs, setFilteredSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    expired: 0,
    expiringSoon: 0
  });

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  useEffect(() => {
    filterSubscriptions();
  }, [subscriptions, searchTerm, statusFilter]);

  const fetchSubscriptions = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/subscriptions/admin/all', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      setSubscriptions(response.data.subscriptions || []);
      calculateStats(response.data.subscriptions || []);
    } catch (error) {
      toast.error('فشل تحميل الاشتراكات');
      console.error('Error fetching subscriptions:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (subs) => {
    const now = new Date();
    const stats = {
      total: subs.length,
      active: 0,
      expired: 0,
      expiringSoon: 0
    };

    subs.forEach(sub => {
      if (sub.status === 'active') {
        stats.active++;
        const endDate = new Date(sub.end_date);
        const daysRemaining = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
        if (daysRemaining <= 14) stats.expiringSoon++;
      } else if (sub.status === 'expired') {
        stats.expired++;
      }
    });

    setStats(stats);
  };

  const filterSubscriptions = () => {
    let filtered = [...subscriptions];

    if (searchTerm) {
      filtered = filtered.filter(sub =>
        sub.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        sub.user_email?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      if (statusFilter === 'expiring_soon') {
        const now = new Date();
        filtered = filtered.filter(sub => {
          if (sub.status !== 'active') return false;
          const endDate = new Date(sub.end_date);
          const daysRemaining = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
          return daysRemaining <= 14;
        });
      } else {
        filtered = filtered.filter(sub => sub.status === statusFilter);
      }
    }

    setFilteredSubs(filtered);
  };

  const getDaysRemaining = (endDate) => {
    const end = new Date(endDate);
    const now = new Date();
    const diffTime = end - now;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const getStatusBadge = (subscription) => {
    const daysRemaining = getDaysRemaining(subscription.end_date);

    if (subscription.status === 'expired') {
      return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> منتهي</Badge>;
    }

    if (daysRemaining <= 0) {
      return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> ينتهي اليوم</Badge>;
    }

    if (daysRemaining <= 7) {
      return <Badge variant="destructive" className="gap-1"><AlertTriangle className="h-3 w-3" /> {daysRemaining} أيام</Badge>;
    }

    if (daysRemaining <= 14) {
      return <Badge variant="warning" className="gap-1"><Clock className="h-3 w-3" /> {daysRemaining} يوماً</Badge>;
    }

    return <Badge variant="success" className="gap-1"><CheckCircle className="h-3 w-3" /> نشط</Badge>;
  };

  const handleExtendSubscription = async (subscriptionId, months = 12) => {
    try {
      await axios.post(`/api/subscriptions/admin/${subscriptionId}/extend`, 
        { months },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      toast.success('تم تمديد الاشتراك بنجاح');
      fetchSubscriptions();
    } catch (error) {
      toast.error('فشل تمديد الاشتراك');
      console.error('Error extending subscription:', error);
    }
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">إجمالي الاشتراكات</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-green-500" />
              نشط
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              على وشك الانتهاء
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats.expiringSoon}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <UserX className="h-4 w-4 text-red-500" />
              منتهي
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.expired}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <CardTitle>إدارة الاشتراكات</CardTitle>
              <CardDescription>عرض وإدارة جميع اشتراكات المستخدمين</CardDescription>
            </div>
            <div className="flex gap-2 w-full md:w-auto">
              <div className="relative flex-1 md:w-64">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="بحث بالاسم أو البريد..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pr-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="الحالة" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">الكل</SelectItem>
                  <SelectItem value="active">نشط</SelectItem>
                  <SelectItem value="expiring_soon">على وشك الانتهاء</SelectItem>
                  <SelectItem value="expired">منتهي</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={fetchSubscriptions} variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>المستخدم</TableHead>
                  <TableHead>البريد الإلكتروني</TableHead>
                  <TableHead>الخطة</TableHead>
                  <TableHead>تاريخ البدء</TableHead>
                  <TableHead>تاريخ الانتهاء</TableHead>
                  <TableHead>الحالة</TableHead>
                  <TableHead>فترة السماح</TableHead>
                  <TableHead className="text-left">الإجراءات</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500 py-8">
                      لا توجد اشتراكات
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredSubs.map((sub) => (
                    <TableRow key={sub.subscription_id}>
                      <TableCell className="font-medium">{sub.user_name || 'غير محدد'}</TableCell>
                      <TableCell>{sub.user_email || 'غير محدد'}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{sub.plan === 'annual' ? 'سنوي' : sub.plan}</Badge>
                      </TableCell>
                      <TableCell>
                        {sub.start_date ? new Date(sub.start_date).toLocaleDateString('ar-YE') : '-'}
                      </TableCell>
                      <TableCell>
                        {sub.end_date ? new Date(sub.end_date).toLocaleDateString('ar-YE') : '-'}
                      </TableCell>
                      <TableCell>{getStatusBadge(sub)}</TableCell>
                      <TableCell>
                        {sub.grace_period_enabled ? (
                          <Badge variant="outline" className="gap-1">
                            <CheckCircle className="h-3 w-3" /> مفعلة
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="gap-1">
                            <XCircle className="h-3 w-3" /> غير مفعلة
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-left">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleExtendSubscription(sub.subscription_id)}
                        >
                          <Calendar className="h-4 w-4 ml-2" />
                          تمديد سنة
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminSubscriptionsPanel;
