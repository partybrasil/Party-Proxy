import sys
import os
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Set

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QGroupBox, QFrame, QSplitter, QListWidget, QStackedWidget,
    QMessageBox, QAbstractItemView, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize
from PySide6.QtGui import QColor, QPalette, QFont, QIcon, QBrush

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import logging
import json

# Import our proxy manager
from party_proxy import ProxyManager, logger

class WorkerSignals(QObject):
    """Signals for background tasks"""
    progress = Signal(int, int, object)
    scraped = Signal(set)
    finished = Signal(list)
    log = Signal(str)
    error = Signal(str)

class QtLoggingHandler(logging.Handler):
    """Custom logging handler to redirect logs to the GUI"""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)

class ScrapeWorker(threading.Thread):
    """Worker thread for background scraping"""
    def __init__(self, manager: ProxyManager, signals: WorkerSignals, max_workers: int = 100):
        super().__init__()
        self.manager = manager
        self.signals = signals
        self.max_workers = max_workers
        self._is_running = True

    def run(self):
        try:
            raw_proxies = self.manager.scrape_proxies(
                cancel_check=self.is_cancelled, 
                max_workers=self.max_workers
            )
            # Emit regardless of _is_running so partial results are shown on stop
            if raw_proxies:
                self.signals.scraped.emit(raw_proxies)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit([])

    def is_cancelled(self):
        return not self._is_running

    def stop(self):
        self._is_running = False

class ProxyWorker(threading.Thread):
    """Worker thread for non-blocking proxy operations"""
    def __init__(self, manager: ProxyManager, proxies_to_check: Set[str], signals: WorkerSignals, max_workers: int = 100):
        super().__init__()
        self.manager = manager
        self.proxies_to_check = proxies_to_check
        self.signals = signals
        self.max_workers = max_workers
        self._is_running = True

    def run(self):
        try:
            # We check in batches or one by one to allow interruption
            working_proxies = []
            total = len(self.proxies_to_check)
            checked = 0
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            with self.executor:
                future_to_proxy = {self.executor.submit(self.manager.check_proxy, proxy): proxy for proxy in self.proxies_to_check}
                
                for future in as_completed(future_to_proxy):
                    if not self._is_running:
                        self.executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    checked += 1
                    try:
                        result = future.result()
                        if result:
                            working_proxies.append(result)
                        self.signals.progress.emit(checked, total, result)
                    except Exception as e:
                        logger.error(f"Error in future result: {e}")
            
            if self._is_running:
                self.signals.finished.emit(working_proxies)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit([])

    def stop(self):
        self._is_running = False
        if hasattr(self, 'executor'):
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except:
                pass

class DashboardWidget(QWidget):
    """Dashboard view with charts and stats"""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        # Stats Cards
        self.stats_layout = QHBoxLayout()
        self.total_card = self.create_stat_card("Total Proxies", "0", "#3498db")
        self.active_card = self.create_stat_card("Active", "0", "#2ecc71")
        self.latency_card = self.create_stat_card("Avg Latency", "0 ms", "#f1c40f")
        self.stats_layout.addWidget(self.total_card)
        self.stats_layout.addWidget(self.active_card)
        self.stats_layout.addWidget(self.latency_card)
        self.layout.addLayout(self.stats_layout)
        
        # Charts Area
        self.chart_frame = QFrame()
        self.chart_layout = QHBoxLayout(self.chart_frame)
        
        self.figure, self.ax = plt.subplots(figsize=(5, 4), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.chart_layout.addWidget(self.canvas)
        
        self.layout.addWidget(self.chart_frame)
        self.update_chart([], [])

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white;")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10))
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.value_label = value_label # Save reference
        return card

    def update_stats(self, total, active, avg_latency):
        self.total_card.value_label.setText(str(total))
        self.active_card.value_label.setText(str(active))
        self.latency_card.value_label.setText(f"{avg_latency:.0f} ms")

    def update_chart(self, labels, values):
        self.ax.clear()
        if not values or sum(values) == 0:
            self.ax.text(0.5, 0.5, "No Data", ha='center', va='center')
        else:
            self.ax.pie(values, labels=labels, autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c', '#95a5a6'])
        self.canvas.draw()

class ProxyTableWidget(QTableWidget):
    """Proxy list with filtering and selection"""
    def __init__(self):
        super().__init__(0, 6)
        self.setHorizontalHeaderLabels(["Proxy", "Country", "Privacy", "Latency", "Rank", "Last Check"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)  # Enable column sorting

    def add_proxy_row(self, proxy_info: Dict[str, Any]):
        # Temporarily disable sorting to prevent None errors during addition
        was_sorting = self.isSortingEnabled()
        self.setSortingEnabled(False)
        
        row = self.rowCount()
        self.insertRow(row)
        
        proxy_item = QTableWidgetItem(proxy_info['proxy'])
        proxy_item.setData(Qt.UserRole, proxy_info.get('status', 'active'))
        self.setItem(row, 0, proxy_item)
        
        self.setItem(row, 1, QTableWidgetItem(f"{proxy_info.get('countryCode', '??')} {proxy_info.get('country', 'Unknown')}"))
        self.setItem(row, 2, QTableWidgetItem(proxy_info.get('privacy', 'Unknown')))
        self.setItem(row, 3, QTableWidgetItem(f"{proxy_info['latency']} ms"))
        
        # Rank placeholder
        rank_item = QTableWidgetItem("")
        rank_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 4, rank_item)
        
        self.setItem(row, 5, QTableWidgetItem(proxy_info.get('last_check', 'N/A')))
        
        # Color based on latency
        color = QColor("#2ecc71") if proxy_info['latency'] < 500 else QColor("#f1c40f")
        if proxy_info['latency'] > 1000: color = QColor("#e67e22")
        self.item(row, 3).setForeground(QBrush(color))
        
        # Re-enable sorting if it was enabled
        self.setSortingEnabled(was_sorting)

    def update_rankings(self):
        """Update star rankings based on relative latencies"""
        row_count = self.rowCount()
        active_latencies = []
        
        for i in range(row_count):
            item = self.item(i, 3)
            if not item:  # Skip if item is None
                continue
            lat_text = item.text().replace(' ms', '')
            try:
                # Latency can be a float
                lat = float(lat_text)
                if lat > 0:
                    active_latencies.append((i, lat))
            except:
                continue
        
        if not active_latencies:
            return
            
        # Sort by latency
        active_latencies.sort(key=lambda x: x[1])
        total = len(active_latencies)
        
        for idx, (row, lat) in enumerate(active_latencies):
            # Calculate stars (relative rank)
            percentile = (idx / total)
            if percentile < 0.2: stars = "⭐⭐⭐⭐⭐"
            elif percentile < 0.4: stars = "⭐⭐⭐⭐"
            elif percentile < 0.6: stars = "⭐⭐⭐"
            elif percentile < 0.8: stars = "⭐⭐"
            else: stars = "⭐"
            
            self.item(row, 4).setText(stars)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Party-Proxy GUI")
        self.resize(1100, 750)
        
        self.manager = ProxyManager()
        self.active_proxies: List[Dict[str, Any]] = []
        self.proxy_set: Set[str] = set()
        self.current_worker = None
        
        # Setup Logger redirection
        self.setup_logging()
        
        self.setup_ui()
        self.load_initial_data()
    
    def closeEvent(self, event):
        """Save proxy data before closing"""
        self.save_proxy_cache()
        event.accept()
    
    def save_proxy_cache(self):
        """Save all proxy data to JSON file"""
        cache_file = os.path.join(self.manager.output_dir, 'proxy_cache.json')
        proxy_data = []
        
        for i in range(self.table.rowCount()):
            # Skip rows with None items
            if not all([self.table.item(i, j) for j in range(6)]):
                continue
                
            proxy_data.append({
                'proxy': self.table.item(i, 0).text(),
                'status': self.table.item(i, 0).data(Qt.UserRole),
                'country': self.table.item(i, 1).text().split(' ', 1)[1] if ' ' in self.table.item(i, 1).text() else 'Unknown',
                'countryCode': self.table.item(i, 1).text().split(' ', 1)[0] if ' ' in self.table.item(i, 1).text() else '??',
                'privacy': self.table.item(i, 2).text(),
                'latency': float(self.table.item(i, 3).text().replace(' ms', '')) if 'ms' in self.table.item(i, 3).text() else 0,
                'last_check': self.table.item(i, 5).text()
            })
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(proxy_data, f, indent=2)
            self.log(f"Saved {len(proxy_data)} proxies to cache.")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def setup_logging(self):
        self.log_signals = WorkerSignals()
        self.log_signals.log.connect(self.log)
        
        handler = QtLoggingHandler(self.log_signals.log)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #2c3e50; color: white;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        btn_dashboard = QPushButton("Dashboard")
        btn_list = QPushButton("Proxy List")
        
        for btn in [btn_dashboard, btn_list]:
            btn.setStyleSheet("text-align: left; padding: 10px; border: none; font-size: 14px;")
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        
        # Stacked Content
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Views
        self.dashboard_view = DashboardWidget()
        self.proxy_list_view = QWidget()
        self.setup_proxy_list_view()
        
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.proxy_list_view)
        
        # Connections
        btn_dashboard.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_list.clicked.connect(lambda: self.stack.setCurrentIndex(1))

    def setup_proxy_list_view(self):
        layout = QVBoxLayout(self.proxy_list_view)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search proxy...")
        btn_check_selected = QPushButton("Check Selected")
        btn_check_all = QPushButton("Check All")
        btn_scrape_now = QPushButton("Scrape & Check")
        btn_scrape_now.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        
        toolbar.addWidget(self.search_input)
        
        self.workers_input = QLineEdit()
        self.workers_input.setPlaceholderText("Workers (1-9999)")
        self.workers_input.setFixedWidth(120)
        toolbar.addWidget(self.workers_input)

        self.btn_scrape_only = QPushButton("Scrape Only")
        self.btn_scrape_now = QPushButton("Scrape & Check")
        self.btn_scrape_now.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_check_selected = QPushButton("Check Selected")
        self.btn_check_all = QPushButton("Check All")
        
        toolbar.addWidget(self.btn_scrape_only)
        toolbar.addWidget(self.btn_scrape_now)
        toolbar.addWidget(self.btn_check_selected)
        toolbar.addWidget(self.btn_check_all)
        layout.addLayout(toolbar)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Table
        self.table = ProxyTableWidget()
        layout.addWidget(self.table)
        
        # Log view
        self.log_view = QListWidget()
        self.log_view.setMaximumHeight(100)
        layout.addWidget(self.log_view)
        
        # Connections
        self.btn_scrape_only.clicked.connect(self.toggle_scrape_only)
        self.btn_scrape_now.clicked.connect(self.toggle_full_scan)
        self.btn_check_selected.clicked.connect(self.toggle_check_selected)
        self.btn_check_all.clicked.connect(self.toggle_check_all)

    def load_initial_data(self):
        """Load proxies from JSON cache if available, otherwise from txt"""
        cache_file = os.path.join(self.manager.output_dir, 'proxy_cache.json')
        
        # Try to load from JSON first
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    proxy_data = json.load(f)
                
                self.log(f"Loaded {len(proxy_data)} proxies from cache.")
                for p in proxy_data:
                    self.proxy_set.add(p['proxy'])
                    self.table.add_proxy_row(p)
                return
            except Exception as e:
                logger.error(f"Error loading JSON cache: {e}")
        
        # Fallback to txt file
        cached = self.manager.load_cached_proxies()
        self.log(f"Loaded {len(cached)} proxies from txt cache.")
        for p in cached:
            self.proxy_set.add(p)
            # Fake initial check info for display
            self.table.add_proxy_row({
                'proxy': p, 
                'latency': 0, 
                'status': 'cached',
                'country': 'Unknown',
                'countryCode': '??',
                'privacy': 'Unknown',
                'last_check': 'Never'
            })

    def log(self, text):
        item = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        self.log_view.addItem(item)
        self.log_view.scrollToBottom()

    def toggle_scrape_only(self):
        if self.current_worker and self.current_worker.is_alive():
            self.stop_current_operation()
        else:
            self.start_scrape_only()

    def start_scrape_only(self):
        max_workers = self.get_worker_count()
        self.log(f"Scraping proxies (No check) using {max_workers} workers...")
        self.btn_scrape_only.setText("Stop Scrape")
        self.btn_scrape_only.setStyleSheet("background-color: #c0392b; color: white;")
        
        signals = WorkerSignals()
        signals.scraped.connect(self.on_proxies_scraped)
        signals.finished.connect(self.on_operation_finished)
        signals.error.connect(self.on_worker_error)
        
        self.current_worker = ScrapeWorker(self.manager, signals, max_workers=max_workers)
        self.current_worker.start()

    def get_worker_count(self):
        worker_text = self.workers_input.text().strip()
        if worker_text.isdigit():
            val = int(worker_text)
            if 1 <= val <= 9999:
                return val
        return 100 # Default

    def on_proxies_scraped(self, raw_proxies):
        added_count = 0
        self.table.setUpdatesEnabled(False)
        try:
            for p in raw_proxies:
                if p not in self.proxy_set:
                    self.table.add_proxy_row({
                        'proxy': p, 
                        'latency': 0, 
                        'status': 'raw',
                        'country': 'Unknown',
                        'countryCode': '??',
                        'privacy': 'Unknown'
                    })
                    self.proxy_set.add(p)
                    added_count += 1
        finally:
            self.table.setUpdatesEnabled(True)
            
        self.log(f"Scrape finished. Added {added_count} new proxies.")
        self.update_dashboard_stats()

    def is_proxy_in_table(self, proxy_str):
        return proxy_str in self.proxy_set

    def toggle_full_scan(self):
        if self.current_worker and self.current_worker.is_alive():
            self.stop_current_operation()
        else:
            self.start_full_scan()

    def start_full_scan(self):
        max_workers = self.get_worker_count()
        self.log(f"Starting full scrape and scan using {max_workers} workers...")
        self.btn_scrape_now.setText("Stop Scrape & Check")
        self.btn_scrape_now.setStyleSheet("background-color: #c0392b; color: white;")
        
        signals = WorkerSignals()
        signals.scraped.connect(self.start_check_after_scrape)
        signals.error.connect(self.on_worker_error)
        
        self.current_worker = ScrapeWorker(self.manager, signals, max_workers=max_workers)
        self.current_worker.start()

    def start_check_after_scrape(self, raw_proxies):
        self.run_worker(raw_proxies)

    def stop_current_operation(self):
        if self.current_worker:
            self.log("Stopping operation requested...")
            self.current_worker.stop()
            # If it's a scrape worker, it might take a moment to hit the check.
            # Force UI update if it doesn't happen in 1s
            QTimer.singleShot(1000, self.on_operation_finished)

    def on_operation_finished(self):
        self.btn_scrape_only.setText("Scrape Only")
        self.btn_scrape_only.setStyleSheet("")
        self.btn_scrape_now.setText("Scrape & Check")
        self.btn_scrape_now.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_check_selected.setText("Check Selected")
        self.btn_check_selected.setStyleSheet("")
        self.btn_check_all.setText("Check All")
        self.btn_check_all.setStyleSheet("")
        
        self.progress_bar.hide()
        self.current_worker = None

    def on_worker_error(self, message):
        self.log(f"Error: {message}")
        QMessageBox.critical(self, "Worker Error", message)

    def toggle_check_all(self):
        if self.current_worker and self.current_worker.is_alive():
            self.stop_current_operation()
        else:
            self.check_all_proxies()

    def check_all_proxies(self):
        proxies_to_check = {self.table.item(i, 0).text() for i in range(self.table.rowCount())}
        if not proxies_to_check:
            QMessageBox.information(self, "No proxies", "No proxies in the list to check.")
            return
        self.log(f"Checking all {len(proxies_to_check)} proxies...")
        self.btn_check_all.setText("Stop Check All")
        self.btn_check_all.setStyleSheet("background-color: #c0392b; color: white;")
        self.run_worker(proxies_to_check)

    def toggle_check_selected(self):
        if self.current_worker and self.current_worker.is_alive():
            self.stop_current_operation()
        else:
            self.check_selected_proxies()

    def check_selected_proxies(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No selection", "Please select one or more proxies.")
            return
        
        proxies_to_check = {self.table.item(row.row(), 0).text() for row in selected_rows}
        self.log(f"Checking {len(proxies_to_check)} selected proxies...")
        self.btn_check_selected.setText("Stop Check Selected")
        self.btn_check_selected.setStyleSheet("background-color: #c0392b; color: white;")
        self.run_worker(proxies_to_check)

    def run_worker(self, proxies_set):
        max_workers = self.get_worker_count()
        self.log(f"Launching worker with {max_workers} threads.")
        
        # Mark proxies being checked as 'checking'
        for i in range(self.table.rowCount()):
            proxy_str = self.table.item(i, 0).text()
            if proxy_str in proxies_set:
                self.table.item(i, 0).setData(Qt.UserRole, 'checking')

        self.progress_bar.setMaximum(len(proxies_set))
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        signals = WorkerSignals()
        signals.progress.connect(self.on_worker_progress)
        signals.finished.connect(self.on_worker_finished)
        signals.error.connect(self.on_worker_error)
        
        self.current_worker = ProxyWorker(self.manager, proxies_set, signals, max_workers=max_workers)
        self.current_worker.start()

    def on_worker_progress(self, current, total, result):
        self.progress_bar.setValue(current)
        if result:
            self.log(f"✓ Found active: {result['proxy']} ({result['country']}, {result['privacy']}, {result['latency']}ms)")
            # Update existing or add new
            self.update_table_with_result(result)
            self.table.update_rankings()
            self.update_dashboard_stats()

    def update_table_with_result(self, result):
        # Update set and handle UI
        self.proxy_set.add(result['proxy'])
        
        # Look for existing row to update
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == result['proxy']:
                # Update existing row
                self.table.removeRow(i)
                break
        
        # Add as new row (which is actually updated info)
        self.table.add_proxy_row(result)

    def on_worker_finished(self, working_proxies):
        # Remove only proxies with 'checking' status after checking is complete
        # These are proxies that were checked but failed (never upgraded to 'active')
        rows_to_delete = []
        for i in range(self.table.rowCount()):
            status = self.table.item(i, 0).data(Qt.UserRole)
            if status == 'checking':  # Only remove proxies that were being checked and failed
                proxy_str = self.table.item(i, 0).text()
                rows_to_delete.append((i, proxy_str))
        
        # Delete rows in reverse order to maintain indices
        for row, proxy in reversed(rows_to_delete):
            self.table.removeRow(row)
            self.proxy_set.discard(proxy)
            
        if rows_to_delete:
            self.log(f"Removed {len(rows_to_delete)} dead proxies from list.")
        
        # Count actual active proxies in table
        active_count = sum(1 for i in range(self.table.rowCount()) 
                          if self.table.item(i, 0).data(Qt.UserRole) == 'active')
        
        self.on_operation_finished()
        if working_proxies:  # Only save if we have proxies to save
            self.manager.save_proxies(working_proxies)
        self.log(f"Check finished. {active_count} proxies remain active in list.")
        self.update_dashboard_stats()

    def update_dashboard_stats(self):
        row_count = self.table.rowCount()
        active_count = 0
        latencies = []
        
        for i in range(row_count):
            # Skip rows with None items
            if not self.table.item(i, 0) or not self.table.item(i, 3):
                continue
                
            status = self.table.item(i, 0).data(Qt.UserRole)
            if status == 'active':
                active_count += 1
                lat_text = self.table.item(i, 3).text().split(' ')[0]
                try:
                    # Latency can be a float
                    latencies.append(float(lat_text))
                except:
                    pass
        
        avg_latency = np.mean(latencies) if latencies else 0
        self.dashboard_view.update_stats(row_count, active_count, avg_latency)
        
        # Chart: Active vs Inactive (here using cached as inactive for simplicity)
        labels = ['Active', 'Other']
        values = [active_count, row_count - active_count]
        self.dashboard_view.update_chart(labels, values)
        self.table.update_rankings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
