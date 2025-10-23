import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const PaymentHistory = () => {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/api/payments', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPayments(response.data.payments || []);
      setLoading(false);
      setRefreshing(false);
    } catch (error) {
      console.error('Error fetching payments:', error);
      toast.error('حدث خطأ أثناء تحميل سجل المدفوعات');
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchPayments();
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { label: 'قيد المراجعة', className: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
      approved: { label: 'مقبول', className: 'bg-green-100 text-green-800 border-green-300' },
      rejected: { label: 'مرفوض', className: 'bg-red-100 text-red-800 border-red-300' }
    };

    const config = statusConfig[status] || { label: status, className: '' };
    return (
      <Badge className={config.className}>
        {config.label}
      </Badge>
    );
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-YE', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" dir="rtl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-2xl">سجل المدفوعات</CardTitle>
            <Button 
              onClick={handleRefresh} 
              disabled={refreshing}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 ml-2 ${refreshing ? 'animate-spin' : ''}`} />
              تحديث
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {payments.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle className="h-12 w-12 text-gray-400 mb-4" />
              <p className="text-lg text-gray-600">لا توجد مدفوعات</p>
              <p className="text-sm text-gray-500 mt-2">لم تقم بأي عمليات دفع حتى الآن</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-right">التاريخ</TableHead>
                    <TableHead className="text-right">المبلغ</TableHead>
                    <TableHead className="text-right">الحالة</TableHead>
                    <TableHead className="text-right">اسم المُرسل</TableHead>
                    <TableHead className="text-right">رقم المرجع</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((payment) => (
                    <TableRow key={payment.payment_id}>
                      <TableCell className="text-right">
                        {formatDate(payment.payment_date || payment.created_at)}
                      </TableCell>
                      <TableCell className="text-right font-semibold">
                        {payment.amount.toLocaleString('ar-YE')} ريال
                      </TableCell>
                      <TableCell className="text-right">
                        {getStatusBadge(payment.status)}
                      </TableCell>
                      <TableCell className="text-right">
                        {payment.sender_name}
                      </TableCell>
                      <TableCell className="text-right text-gray-600">
                        {payment.transaction_reference || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentHistory;
