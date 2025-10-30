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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar, Search, RefreshCw, Filter, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from '@/lib/toast';

export const AuditLogViewer = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    action_type: '',
    user_id: '',
    from_date: '',
    to_date: '',
    page: 1,
    per_page: 50
  });
  const [pagination, setPagination] = useState({
    total: 0,
    pages: 0,
    current_page: 1
  });

  const actionTypes = [
    { value: 'login_success', label: 'تسجيل دخول ناجح' },
    { value: 'login_failed', label: 'فشل تسجيل دخول' },
    { value: 'password_changed', label: 'تغيير كلمة المرور' },
    { value: 'role_changed', label: 'تغيير الدور' },
    { value: '2fa_enabled', label: 'تفعيل 2FA' },
    { value: '2fa_disabled', label: 'تعطيل 2FA' },
    { value: 'user_created', label: 'إنشاء مستخدم' },
    { value: 'user_deleted', label: 'حذف مستخدم' },
    { value: 'complaint_created', label: 'إنشاء شكوى' },
    { value: 'complaint_updated', label: 'تحديث شكوى' },
    { value: 'status_changed', label: 'تغيير الحالة' },
    { value: 'assignment_changed', label: 'تغيير التعيين' }
  ];

  useEffect(() => {
    fetchLogs();
  }, [filters.page]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const response = await axios.get(`/api/security/audit-log?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      setLogs(response.data.logs || []);
      setPagination({
        total: response.data.total,
        pages: response.data.pages,
        current_page: response.data.current_page
      });
    } catch (error) {
      toast.error('فشل تحميل سجل الأحداث');
      console.error('Audit log error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const handlePageChange = (newPage) => {
    setFilters(prev => ({ ...prev, page: newPage }));
  };

  const applyFilters = () => {
    fetchLogs();
  };

  const clearFilters = () => {
    setFilters({
      action_type: '',
      user_id: '',
      from_date: '',
      to_date: '',
      page: 1,
      per_page: 50
    });
    setTimeout(fetchLogs, 100);
  };

  const exportToCSV = () => {
    try {
      if (logs.length === 0) {
        toast.error('لا توجد بيانات للتصدير');
        return;
      }

      const csvData = logs.map(log => ({
        'التوقيت': log.timestamp ? new Date(log.timestamp).toLocaleString('ar-YE') : '',
        'النوع': log.action_type || '',
        'المنفذ': log.performed_by_name || '',
        'المتأثر': log.affected_user_name || '',
        'القيمة القديمة': log.old_value || '',
        'القيمة الجديدة': log.new_value || '',
        'التفاصيل': log.details || ''
      }));

      const headers = Object.keys(csvData[0]);
      const csvContent = [
        headers.join(','),
        ...csvData.map(row => headers.map(h => `"${row[h]}"`).join(','))
      ].join('\n');

      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `audit-log-${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      
      toast.success('تم تصدير سجل الأحداث');
    } catch (error) {
      toast.error('فشل تصدير البيانات');
      console.error('CSV export error:', error);
    }
  };

  const getActionBadgeColor = (actionType) => {
    if (actionType.includes('failed') || actionType.includes('deleted')) return 'destructive';
    if (actionType.includes('success') || actionType.includes('created')) return 'success';
    if (actionType.includes('changed') || actionType.includes('updated')) return 'warning';
    return 'default';
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">سجل الأحداث الشامل</h1>
          <p className="text-gray-500 mt-1">تتبع جميع التغييرات والأنشطة في النظام</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={exportToCSV} variant="outline">
            <Download className="h-4 w-4 ml-2" />
            تصدير CSV
          </Button>
          <Button onClick={fetchLogs} variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            الفلاتر
          </CardTitle>
          <CardDescription>فلترة السجل حسب المعايير المختلفة</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Select 
              value={filters.action_type} 
              onValueChange={(value) => handleFilterChange('action_type', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="نوع الحدث" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">الكل</SelectItem>
                {actionTypes.map(type => (
                  <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Input
              type="date"
              value={filters.from_date}
              onChange={(e) => handleFilterChange('from_date', e.target.value)}
              placeholder="من تاريخ"
            />

            <Input
              type="date"
              value={filters.to_date}
              onChange={(e) => handleFilterChange('to_date', e.target.value)}
              placeholder="إلى تاريخ"
            />

            <Button onClick={applyFilters} className="w-full">
              تطبيق
            </Button>

            <Button onClick={clearFilters} variant="outline" className="w-full">
              مسح الفلاتر
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>الأحداث ({pagination.total})</CardTitle>
          <CardDescription>صفحة {pagination.current_page} من {pagination.pages}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>التوقيت</TableHead>
                      <TableHead>نوع الحدث</TableHead>
                      <TableHead>المنفذ</TableHead>
                      <TableHead>المستخدم المتأثر</TableHead>
                      <TableHead>التفاصيل</TableHead>
                      <TableHead>القيمة القديمة</TableHead>
                      <TableHead>القيمة الجديدة</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-gray-500 py-8">
                          لا توجد أحداث
                        </TableCell>
                      </TableRow>
                    ) : (
                      logs.map((log) => (
                        <TableRow key={log.log_id}>
                          <TableCell className="whitespace-nowrap">
                            {log.timestamp ? new Date(log.timestamp).toLocaleString('ar-YE') : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={getActionBadgeColor(log.action_type)}>
                              {log.action_type}
                            </Badge>
                          </TableCell>
                          <TableCell>{log.performed_by_name || 'النظام'}</TableCell>
                          <TableCell>{log.affected_user_name || '-'}</TableCell>
                          <TableCell className="max-w-xs truncate">
                            {log.details || '-'}
                          </TableCell>
                          <TableCell className="max-w-xs truncate">
                            {log.old_value || '-'}
                          </TableCell>
                          <TableCell className="max-w-xs truncate">
                            {log.new_value || '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {pagination.pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-500">
                    عرض {logs.length} من أصل {pagination.total} حدث
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.current_page - 1)}
                      disabled={pagination.current_page === 1}
                    >
                      <ChevronRight className="h-4 w-4" />
                      السابق
                    </Button>
                    <div className="flex items-center gap-1">
                      {[...Array(Math.min(5, pagination.pages))].map((_, i) => {
                        const page = i + 1;
                        return (
                          <Button
                            key={page}
                            variant={pagination.current_page === page ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handlePageChange(page)}
                          >
                            {page}
                          </Button>
                        );
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.current_page + 1)}
                      disabled={pagination.current_page === pagination.pages}
                    >
                      التالي
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AuditLogViewer;
