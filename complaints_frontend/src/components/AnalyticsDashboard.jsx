import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  TrendingUp, TrendingDown, Users, FileText, CheckCircle,
  DollarSign, Clock, RefreshCw, Download
} from 'lucide-react';
import { toast } from '@/lib/toast';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export const AnalyticsDashboard = () => {
  const [summary, setSummary] = useState(null);
  const [complaintsBy

Status, setComplaintsByStatus] = useState([]);
  const [complaintsByCategory, setComplaintsByCategory] = useState([]);
  const [complaintsTimeline, setComplaintsTimeline] = useState([]);
  const [revenueData, setRevenueData] = useState([]);
  const [resolutionStats, setResolutionStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [
        summaryRes,
        statusRes,
        categoryRes,
        timelineRes,
        revenueRes,
        resolutionRes
      ] = await Promise.all([
        axios.get('/api/analytics/dashboard/summary', { headers }),
        axios.get('/api/analytics/complaints/by-status', { headers }),
        axios.get('/api/analytics/complaints/by-category', { headers }),
        axios.get('/api/analytics/complaints/timeline', { headers }),
        axios.get('/api/analytics/revenue/monthly', { headers }),
        axios.get('/api/analytics/performance/resolution-time', { headers })
      ]);

      setSummary(summaryRes.data);
      setComplaintsByStatus(statusRes.data);
      setComplaintsByCategory(categoryRes.data);
      setComplaintsTimeline(timelineRes.data);
      setRevenueData(revenueRes.data);
      setResolutionStats(resolutionRes.data);
    } catch (error) {
      toast.error('فشل تحميل بيانات التحليلات');
      console.error('Analytics error:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportToPDF = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/api/export/analytics-pdf', {
        headers: { 'Authorization': `Bearer ${token}` },
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analytics-${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('تم تصدير التقرير بنجاح');
    } catch (error) {
      toast.error('فشل تصدير التقرير');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <RefreshCw className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">لوحة التحكم الإدارية</h1>
          <p className="text-gray-500 mt-1">إحصائيات ومؤشرات الأداء الرئيسية</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchDashboardData} variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={exportToPDF} variant="default">
            <Download className="h-4 w-4 ml-2" />
            تصدير PDF
          </Button>
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">إجمالي الشكاوى</CardTitle>
              <FileText className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_complaints}</div>
              <p className="text-xs text-gray-500 mt-1">
                +{summary.new_complaints_30d} في آخر 30 يوم
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">معدل الحل</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.resolution_rate}%</div>
              <p className="text-xs text-gray-500 mt-1">
                {summary.resolved_complaints} شكوى محلولة
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">المستخدمون</CardTitle>
              <Users className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_users}</div>
              <p className="text-xs text-gray-500 mt-1">
                {summary.total_traders} تاجر
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">متوسط وقت الحل</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {summary.avg_resolution_time_hours ? 
                  `${Math.round(summary.avg_resolution_time_hours)}س` : 
                  'غير محدد'}
              </div>
              <p className="text-xs text-gray-500 mt-1">معدل زمن الحل</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>الشكاوى حسب الحالة</CardTitle>
            <CardDescription>توزيع الشكاوى على الحالات المختلفة</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={complaintsByStatus}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {complaintsByStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>الشكاوى حسب التصنيف</CardTitle>
            <CardDescription>توزيع الشكاوى على التصنيفات</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={complaintsByCategory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>تطور الشكاوى عبر الزمن</CardTitle>
          <CardDescription>عدد الشكاوى المقدمة خلال الأشهر الستة الماضية</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={complaintsTimeline}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" name="عدد الشكاوى" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {revenueData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>الإيرادات الشهرية</CardTitle>
            <CardDescription>إجمالي الإيرادات من الاشتراكات</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="revenue" name="الإيرادات (ريال)" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {resolutionStats && (
        <Card>
          <CardHeader>
            <CardTitle>إحصائيات وقت الحل</CardTitle>
            <CardDescription>توزيع أوقات حل الشكاوى</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">متوسط الوقت</p>
                <p className="text-2xl font-bold">{resolutionStats.avg_hours.toFixed(1)} ساعة</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">أسرع حل</p>
                <p className="text-2xl font-bold">{resolutionStats.min_hours.toFixed(1)} ساعة</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">أبطأ حل</p>
                <p className="text-2xl font-bold">{resolutionStats.max_hours.toFixed(1)} ساعة</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={resolutionStats.distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" name="عدد الشكاوى" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
