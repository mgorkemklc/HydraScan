using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using Microsoft.Win32;

namespace HydraScanUI
{
    public partial class MainWindow : Window
    {
        private static readonly HttpClient client = new HttpClient();
        private DispatcherTimer logTimer;
        private string selectedApkPath = "";

        public MainWindow()
        {
            InitializeComponent();

            // Background log fetcher
            logTimer = new DispatcherTimer();
            logTimer.Interval = TimeSpan.FromSeconds(1);
            logTimer.Tick += FetchLogsAndStats;
            logTimer.Start();
        }

        // Allow Window dragging
        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            this.DragMove();
        }

        private void NavDashboard_Checked(object sender, RoutedEventArgs e)
        {
            if (DashboardView != null && ScanView != null && ReportsView != null)
            {
                DashboardView.Visibility = Visibility.Visible;
                ScanView.Visibility = Visibility.Collapsed;
                ReportsView.Visibility = Visibility.Collapsed;
            }
        }

        private void NavScan_Checked(object sender, RoutedEventArgs e)
        {
            if (DashboardView != null && ScanView != null && ReportsView != null)
            {
                DashboardView.Visibility = Visibility.Collapsed;
                ScanView.Visibility = Visibility.Visible;
                ReportsView.Visibility = Visibility.Collapsed;
            }
        }

        private void NavReports_Checked(object sender, RoutedEventArgs e)
        {
            if (DashboardView != null && ScanView != null && ReportsView != null)
            {
                DashboardView.Visibility = Visibility.Collapsed;
                ScanView.Visibility = Visibility.Collapsed;
                ReportsView.Visibility = Visibility.Visible;
                
                // Automatically refresh reports when tab is opened
                BtnRefreshReports_Click(null, null);
            }
        }

        // Smart text box
        private void TargetInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (TargetInput.Text == "Enter target URL or IP...") TargetInput.Text = "";
        }

        private void TargetInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(TargetInput.Text)) TargetInput.Text = "Enter target URL or IP...";
        }

        // APK Picker
        private void BtnSelectApk_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "APK Files (*.apk)|*.apk|All Files (*.*)|*.*";

            if (openFileDialog.ShowDialog() == true)
            {
                selectedApkPath = openFileDialog.FileName;
                LblApkPath.Text = "Selected File: " + System.IO.Path.GetFileName(selectedApkPath);
            }
        }

        // Start Scan
        private async void StartScan_Click(object sender, RoutedEventArgs e)
        {
            string target = TargetInput.Text;
            string type = "web";
            if (ScanTypeCombo.SelectedIndex == 1) type = "mobile";
            if (ScanTypeCombo.SelectedIndex == 2) type = "network";

            if (string.IsNullOrWhiteSpace(target) || target == "Enter target URL or IP...")
            {
                MessageBox.Show("Please enter a valid target!", "Security Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            // Return to dashboard to see logs
            DashboardView.Visibility = Visibility.Visible;
            ScanView.Visibility = Visibility.Collapsed;
            
            // Uncheck Scan side nav, check Dashboard side nav (this would be better bound via ViewModel, but hardcoding for now)
            // It will visually just change the page.

            try
            {
                var payload = new { target = target, scan_type = type };
                string json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                await client.PostAsync("http://127.0.0.1:8000/api/scan", content);
                
                TerminalOutput.Inlines.Add(new System.Windows.Documents.Run("[*] API request sent for: " + target + "\n") { Foreground = System.Windows.Media.Brushes.SpringGreen });
            }
            catch (Exception)
            {
                TerminalOutput.Inlines.Add(new System.Windows.Documents.Run("[-] ERROR: Python API is unreachable. Is 'api_server.py' running?\n") { Foreground = System.Windows.Media.Brushes.IndianRed });
                TerminalScroll.ScrollToEnd();
            }
        }

        // Fetch Logs
        private async void FetchLogsAndStats(object sender, EventArgs e)
        {
            try
            {
                var logRes = await client.GetStringAsync("http://127.0.0.1:8000/api/logs");
                using (JsonDocument doc = JsonDocument.Parse(logRes))
                {
                    foreach (JsonElement log in doc.RootElement.GetProperty("logs").EnumerateArray())
                    {
                        string msg = log.GetString();
                        if (msg.Contains("[-]"))
                            TerminalOutput.Inlines.Add(new System.Windows.Documents.Run(msg + "\n") { Foreground = System.Windows.Media.Brushes.IndianRed });
                        else if (msg.Contains("[+]"))
                            TerminalOutput.Inlines.Add(new System.Windows.Documents.Run(msg + "\n") { Foreground = System.Windows.Media.Brushes.SpringGreen });
                        else
                            TerminalOutput.Text += msg + "\n";
                    }
                    if (doc.RootElement.GetProperty("logs").GetArrayLength() > 0)
                        TerminalScroll.ScrollToEnd();
                }

                var statRes = await client.GetStringAsync("http://127.0.0.1:8000/api/stats");
                using (JsonDocument doc = JsonDocument.Parse(statRes))
                {
                    LblTotal.Text = doc.RootElement.GetProperty("total").GetInt32().ToString("D2");
                    LblActive.Text = doc.RootElement.GetProperty("active").GetInt32().ToString("D2");
                    LblFailed.Text = doc.RootElement.GetProperty("failed").GetInt32().ToString("D2");
                }
            }
            catch { /* Ignore API errors if not running */ }
        }

        // --- REPORTS VIEW LOGIC ---

        public class ReportItem
        {
            public int id { get; set; }
            public string target_full_domain { get; set; }
            public string status { get; set; }
            public string created_at { get; set; }
        }

        public class FindingItem
        {
            public string arac_adi { get; set; }
            public string risk_seviyesi { get; set; }
            public string risk_color { get; set; }
            public string ozet { get; set; }
            public System.Collections.Generic.List<string> bulgular { get; set; }
            public System.Collections.Generic.List<string> oneriler { get; set; }
        }

        private async void BtnRefreshReports_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                BtnRefreshReports.Content = "Loading...";
                var res = await client.GetStringAsync("http://127.0.0.1:8000/api/reports");
                var reports = JsonSerializer.Deserialize<Dictionary<string, System.Collections.Generic.List<ReportItem>>>(res);

                if (reports != null && reports.ContainsKey("reports"))
                {
                    ReportsList.ItemsSource = reports["reports"];
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to load reports: " + ex.Message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                BtnRefreshReports.Content = "🔄 Refresh";
            }
        }

        private async void ReportsList_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (ReportsList.SelectedItem is ReportItem selectedReport)
            {
                if (selectedReport.status != "COMPLETED")
                {
                    LblReportDetailTitle.Text = $"Report is not ready yet ({selectedReport.status})";
                    ReportFindingsList.ItemsSource = null;
                    return;
                }

                try
                {
                    LblReportDetailTitle.Text = $"Loading {selectedReport.target_full_domain}...";
                    ReportFindingsList.ItemsSource = null;

                    var res = await client.GetStringAsync($"http://127.0.0.1:8000/api/reports/{selectedReport.id}");
                    using (JsonDocument doc = JsonDocument.Parse(res))
                    {
                        var root = doc.RootElement;
                        if (root.TryGetProperty("error", out JsonElement errorMsg))
                        {
                            LblReportDetailTitle.Text = "Error: " + errorMsg.GetString();
                            return;
                        }

                        LblReportDetailTitle.Text = $"Analysis Report: {selectedReport.target_full_domain}";

                        var parsedFindings = new System.Collections.Generic.List<FindingItem>();
                        if (root.TryGetProperty("report_data", out JsonElement reportData) && 
                            reportData.TryGetProperty("analizler", out JsonElement analizler))
                        {
                            foreach (var analiz in analizler.EnumerateArray())
                            {
                                var item = new FindingItem
                                {
                                    arac_adi = analiz.GetProperty("arac_adi").GetString(),
                                    risk_seviyesi = analiz.GetProperty("risk_seviyesi").GetString(),
                                    ozet = analiz.GetProperty("ozet").GetString(),
                                    bulgular = new System.Collections.Generic.List<string>(),
                                    oneriler = new System.Collections.Generic.List<string>()
                                };

                                // Assign color based on risk
                                string riskUpper = item.risk_seviyesi.ToUpper();
                                if (riskUpper.Contains("KRITIK") || riskUpper.Contains("HIGH") || riskUpper.Contains("YÜKSEK"))
                                    item.risk_color = "#EF4444"; // Red
                                else if (riskUpper.Contains("ORTA") || riskUpper.Contains("MEDIUM"))
                                    item.risk_color = "#F59E0B"; // Orange
                                else if (riskUpper.Contains("BİLGİ") || riskUpper.Contains("INFO"))
                                    item.risk_color = "#3B82F6"; // Blue
                                else
                                    item.risk_color = "#10B981"; // Green (Low)

                                if (analiz.TryGetProperty("bulgular", out JsonElement bList))
                                {
                                    foreach (var b in bList.EnumerateArray())
                                        item.bulgular.Add("• " + b.GetString());
                                }

                                if (analiz.TryGetProperty("oneriler", out JsonElement oList))
                                {
                                    foreach (var o in oList.EnumerateArray())
                                        item.oneriler.Add("🛡️ " + o.GetString());
                                }

                                parsedFindings.Add(item);
                            }
                        }

                        ReportFindingsList.ItemsSource = parsedFindings;
                        if (parsedFindings.Count == 0)
                        {
                            LblReportDetailTitle.Text = $"No findings in report for {selectedReport.target_full_domain}";
                        }
                    }
                }
                catch (Exception ex)
                {
                    LblReportDetailTitle.Text = "Failed to load report data.";
                    MessageBox.Show(ex.Message, "Error");
                }
            }
        }
    }
}