"""
Performance monitoring utilities for MemeZap.
"""
import time
import logging
import psutil
import os
from functools import wraps
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and log performance metrics for meme generation."""
    
    def __init__(self, log_file="data/performance_logs.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = []
        
    def log_metric(self, operation, duration, memory_usage=None, additional_data=None):
        """Log a performance metric."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_seconds": duration,
            "memory_mb": memory_usage,
            "additional_data": additional_data or {}
        }
        
        self.metrics.append(metric)
        
        # Write to file periodically
        if len(self.metrics) >= 10:
            self._write_metrics()
    
    def _write_metrics(self):
        """Write metrics to file."""
        try:
            existing_metrics = []
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    existing_metrics = json.load(f)
            
            existing_metrics.extend(self.metrics)
            
            with open(self.log_file, 'w') as f:
                json.dump(existing_metrics, f, indent=2)
            
            self.metrics = []
            
        except Exception as e:
            logger.warning(f"Failed to write performance metrics: {e}")
    
    def get_average_duration(self, operation, last_n=10):
        """Get average duration for an operation."""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    all_metrics = json.load(f)
                
                operation_metrics = [m for m in all_metrics if m["operation"] == operation]
                recent_metrics = operation_metrics[-last_n:] if operation_metrics else []
                
                if recent_metrics:
                    avg_duration = sum(m["duration_seconds"] for m in recent_metrics) / len(recent_metrics)
                    return avg_duration
            
            return None
        except Exception as e:
            logger.warning(f"Failed to get average duration: {e}")
            return None

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def time_operation(operation_name):
    """Decorator to time operations and log performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                duration = end_time - start_time
                memory_delta = end_memory - start_memory
                
                additional_data = {
                    "success": success,
                    "error": error,
                    "memory_delta_mb": memory_delta
                }
                
                performance_monitor.log_metric(
                    operation_name, 
                    duration, 
                    end_memory, 
                    additional_data
                )
                
                logger.info(f"{operation_name} completed in {duration:.2f}s (Memory: {memory_delta:+.1f}MB)")
            
            return result
        return wrapper
    return decorator

def log_system_info():
    """Log system information for performance analysis."""
    try:
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024
        
        # Check GPU availability
        gpu_available = False
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            gpu_name = torch.cuda.get_device_name(0) if gpu_available else "None"
        except ImportError:
            gpu_name = "PyTorch not available"
        
        system_info = {
            "cpu_cores": cpu_count,
            "memory_gb": round(memory_gb, 1),
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
        }
        
        logger.info(f"System Info: {system_info}")
        return system_info
        
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        return {}

def get_performance_summary():
    """Get a summary of recent performance metrics."""
    try:
        log_file = Path("data/performance_logs.json")
        if not log_file.exists():
            return {"message": "No performance data available"}
        
        with open(log_file, 'r') as f:
            metrics = json.load(f)
        
        if not metrics:
            return {"message": "No performance data available"}
        
        # Get recent metrics (last 24 hours)
        recent_metrics = []
        now = datetime.now()
        
        for metric in metrics:
            try:
                metric_time = datetime.fromisoformat(metric["timestamp"])
                hours_ago = (now - metric_time).total_seconds() / 3600
                if hours_ago <= 24:
                    recent_metrics.append(metric)
            except:
                continue
        
        if not recent_metrics:
            return {"message": "No recent performance data"}
        
        # Calculate averages by operation
        operations = {}
        for metric in recent_metrics:
            op = metric["operation"]
            if op not in operations:
                operations[op] = []
            operations[op].append(metric["duration_seconds"])
        
        summary = {}
        for op, durations in operations.items():
            summary[op] = {
                "count": len(durations),
                "avg_duration": round(sum(durations) / len(durations), 2),
                "min_duration": round(min(durations), 2),
                "max_duration": round(max(durations), 2)
            }
        
        return {
            "recent_operations": len(recent_metrics),
            "operations": summary,
            "system_info": log_system_info()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        return {"error": str(e)} 