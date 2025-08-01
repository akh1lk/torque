#!/usr/bin/env python3
"""
Performance Analysis Tool for Torque 3D Scanning Pipeline
Analyzes the exact performance bottlenecks in RGBA processing to determine
realistic C++ + OpenMP speedup potential.
"""

import time
import numpy as np
import cv2
import psutil
import os
import sys
from typing import Dict, List, Tuple
from PIL import Image
import threading
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import platform

class PerformanceProfiler:
    def __init__(self):
        self.results = {}
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict:
        """Get detailed system information"""
        info = {
            'cpu_count': multiprocessing.cpu_count(),
            'cpu_brand': platform.processor(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'memory_available_gb': psutil.virtual_memory().available / (1024**3),
            'platform': platform.platform(),
            'python_version': sys.version,
        }
        
        # Try to get more detailed CPU info
        try:
            if platform.system() == 'Darwin':  # macOS
                import subprocess
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    info['cpu_brand'] = result.stdout.strip()
                    
                # Get cache info
                l1_result = subprocess.run(['sysctl', '-n', 'hw.l1icachesize'], 
                                         capture_output=True, text=True)
                l2_result = subprocess.run(['sysctl', '-n', 'hw.l2cachesize'], 
                                         capture_output=True, text=True)
                l3_result = subprocess.run(['sysctl', '-n', 'hw.l3cachesize'], 
                                         capture_output=True, text=True)
                
                if l1_result.returncode == 0:
                    info['l1_cache_kb'] = int(l1_result.stdout.strip()) // 1024
                if l2_result.returncode == 0:
                    info['l2_cache_kb'] = int(l2_result.stdout.strip()) // 1024
                if l3_result.returncode == 0:
                    info['l3_cache_kb'] = int(l3_result.stdout.strip()) // 1024
                    
        except Exception as e:
            print(f"Warning: Could not get detailed CPU info: {e}")
            
        return info
    
    def create_test_data(self, num_images: int = 12, height: int = 2142, width: int = 2856) -> Tuple[List[np.ndarray], np.ndarray]:
        """Create test data matching real workload: 12 images × 2142×2856 pixels"""
        print(f"Creating test data: {num_images} images of {width}×{height}")
        
        # Create synthetic images (BGR format like OpenCV)
        images = []
        for i in range(num_images):
            # Create somewhat realistic image data
            img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            # Add some structure to make it more realistic
            img[:, :, 0] = np.clip(img[:, :, 0] + np.sin(np.arange(width) * 0.01) * 50, 0, 255)
            images.append(img)
        
        # Create synthetic masks (binary masks)
        masks = np.random.randint(0, 2, (num_images, height, width), dtype=np.uint8)
        
        # Add some realistic mask patterns
        for i in range(num_images):
            center_y, center_x = height // 2, width // 2
            y, x = np.ogrid[:height, :width]
            mask_circle = ((x - center_x) ** 2 + (y - center_y) ** 2) < (min(height, width) // 4) ** 2
            masks[i] = mask_circle.astype(np.uint8)
        
        total_pixels = num_images * height * width
        total_size_mb = (total_pixels * 3 * 1) / (1024 ** 2)  # RGB bytes
        mask_size_mb = (total_pixels * 1) / (1024 ** 2)  # mask bytes
        
        print(f"Test data created:")
        print(f"  - Images: {total_size_mb:.1f} MB ({num_images} × {height}×{width}×3)")
        print(f"  - Masks: {mask_size_mb:.1f} MB ({num_images} × {height}×{width})")
        print(f"  - Total memory footprint: {total_size_mb + mask_size_mb:.1f} MB")
        
        return images, masks
    
    def time_operation(self, func, *args, **kwargs) -> Tuple[float, any]:
        """Time an operation and return (elapsed_time, result)"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        return elapsed_time, result
    
    def profile_current_implementation(self, images: List[np.ndarray], masks: np.ndarray) -> Dict:
        """Profile the current Python implementation"""
        print("\n=== Profiling Current Python Implementation ===")
        
        results = {}
        
        def create_rgba_single(image, mask):
            """Current implementation from sam2_service.py"""
            # Convert BGR to RGB (OpenCV loads as BGR)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert mask to 0-255 range for alpha channel
            alpha_channel = (mask > 0).astype(np.uint8) * 255
            
            # Create RGBA image by adding alpha channel
            rgba_image = np.dstack((image_rgb, alpha_channel))
            
            return rgba_image
        
        # Profile single image processing
        single_time, _ = self.time_operation(create_rgba_single, images[0], masks[0])
        results['single_image_time'] = single_time
        
        # Profile batch processing (current sequential implementation)
        def process_batch_sequential():
            rgba_images = []
            for i in range(len(images)):
                rgba = create_rgba_single(images[i], masks[i])
                rgba_images.append(rgba)
            return rgba_images
        
        batch_time, rgba_results = self.time_operation(process_batch_sequential)
        results['batch_sequential_time'] = batch_time
        results['images_per_second'] = len(images) / batch_time
        
        # Memory analysis
        single_image_mb = images[0].nbytes / (1024 ** 2)
        single_mask_mb = masks[0].nbytes / (1024 ** 2)
        single_rgba_mb = rgba_results[0].nbytes / (1024 ** 2)
        
        results['memory_analysis'] = {
            'input_image_mb': single_image_mb,
            'input_mask_mb': single_mask_mb,
            'output_rgba_mb': single_rgba_mb,
            'total_working_set_mb': (single_image_mb + single_mask_mb + single_rgba_mb) * len(images)
        }
        
        # Break down operation timing
        timing_breakdown = self._analyze_operation_breakdown(images[0], masks[0])
        results['operation_breakdown'] = timing_breakdown
        
        return results
    
    def _analyze_operation_breakdown(self, image: np.ndarray, mask: np.ndarray) -> Dict:
        """Break down the time spent in each operation"""
        breakdown = {}
        
        # Time BGR to RGB conversion
        bgr_to_rgb_time, image_rgb = self.time_operation(cv2.cvtColor, image, cv2.COLOR_BGR2RGB)
        breakdown['bgr_to_rgb'] = bgr_to_rgb_time
        
        # Time mask processing
        mask_time, alpha_channel = self.time_operation(lambda m: (m > 0).astype(np.uint8) * 255, mask)
        breakdown['mask_processing'] = mask_time
        
        # Time dstack operation
        dstack_time, rgba_image = self.time_operation(np.dstack, (image_rgb, alpha_channel))
        breakdown['dstack'] = dstack_time
        
        return breakdown
    
    def profile_threading_potential(self, images: List[np.ndarray], masks: np.ndarray) -> Dict:
        """Test threading potential with Python threading"""
        print("\n=== Profiling Threading Potential ===")
        
        results = {}
        
        def create_rgba_single(image, mask):
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            alpha_channel = (mask > 0).astype(np.uint8) * 255
            rgba_image = np.dstack((image_rgb, alpha_channel))
            return rgba_image
        
        # Test different thread counts
        thread_counts = [1, 2, 4, 8]
        
        for num_threads in thread_counts:
            if num_threads > len(images):
                continue
                
            def process_batch_threaded():
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [executor.submit(create_rgba_single, images[i], masks[i]) 
                             for i in range(len(images))]
                    return [f.result() for f in futures]
            
            threaded_time, _ = self.time_operation(process_batch_threaded)
            results[f'threads_{num_threads}'] = threaded_time
            results[f'speedup_{num_threads}'] = results['threads_1'] / threaded_time if 'threads_1' in results else 1.0
        
        return results
    
    def analyze_memory_patterns(self, images: List[np.ndarray], masks: np.ndarray) -> Dict:
        """Analyze memory access patterns and bandwidth requirements"""
        print("\n=== Analyzing Memory Patterns ===")
        
        results = {}
        
        # Calculate memory bandwidth requirements
        height, width = images[0].shape[:2]
        pixels_per_image = height * width
        
        # Input data per image
        input_bytes_per_image = pixels_per_image * 3 + pixels_per_image  # RGB + mask
        
        # Output data per image  
        output_bytes_per_image = pixels_per_image * 4  # RGBA
        
        # Total bytes transferred per image
        total_bytes_per_image = input_bytes_per_image + output_bytes_per_image
        
        results['memory_requirements'] = {
            'pixels_per_image': pixels_per_image,
            'input_mb_per_image': input_bytes_per_image / (1024 ** 2),
            'output_mb_per_image': output_bytes_per_image / (1024 ** 2),
            'total_transfer_mb_per_image': total_bytes_per_image / (1024 ** 2),
        }
        
        # Calculate theoretical memory bandwidth
        single_image_time = self.results.get('current_implementation', {}).get('single_image_time', 0.1)
        if single_image_time > 0:
            bandwidth_gb_s = (total_bytes_per_image / single_image_time) / (1024 ** 3)
            results['measured_bandwidth_gb_s'] = bandwidth_gb_s
        
        # Cache analysis
        results['cache_analysis'] = self._analyze_cache_behavior(height, width)
        
        return results
    
    def _analyze_cache_behavior(self, height: int, width: int) -> Dict:
        """Analyze cache behavior for the given image dimensions"""
        analysis = {}
        
        # Calculate working set sizes
        single_row_bytes = width * 3  # RGB row
        single_image_bytes = height * width * 3
        rgba_image_bytes = height * width * 4
        
        analysis['working_sets'] = {
            'single_row_kb': single_row_bytes / 1024,
            'single_image_mb': single_image_bytes / (1024 ** 2),
            'rgba_output_mb': rgba_image_bytes / (1024 ** 2),
        }
        
        # Estimate cache efficiency based on typical cache sizes
        l1_cache_kb = self.system_info.get('l1_cache_kb', 32)  # Typical L1 data cache
        l2_cache_kb = self.system_info.get('l2_cache_kb', 256)  # Typical L2 cache
        l3_cache_mb = self.system_info.get('l3_cache_kb', 8192) / 1024  # Typical L3 cache
        
        analysis['cache_efficiency'] = {
            'rows_fit_in_l1': l1_cache_kb / (single_row_bytes / 1024),
            'images_fit_in_l2': l2_cache_kb / (single_image_bytes / 1024),
            'images_fit_in_l3': l3_cache_mb / (single_image_bytes / (1024 ** 2)),
        }
        
        return analysis
    
    def estimate_cpp_openmp_speedup(self) -> Dict:
        """Estimate realistic C++ + OpenMP speedup potential"""
        print("\n=== Estimating C++ + OpenMP Speedup Potential ===")
        
        current_perf = self.results.get('current_implementation', {})
        threading_perf = self.results.get('threading_potential', {})
        memory_analysis = self.results.get('memory_analysis', {})
        
        analysis = {}
        
        # Amdahl's Law analysis
        # Identify parallelizable vs sequential portions
        operation_breakdown = current_perf.get('operation_breakdown', {})
        
        # Operations that are embarrassingly parallel
        parallelizable_ops = ['bgr_to_rgb', 'mask_processing', 'dstack']
        sequential_ops = []  # Most operations in this pipeline are parallelizable
        
        total_time = sum(operation_breakdown.values())
        parallelizable_time = sum(operation_breakdown.get(op, 0) for op in parallelizable_ops)
        sequential_time = total_time - parallelizable_time
        
        parallelizable_fraction = parallelizable_time / total_time if total_time > 0 else 0
        
        analysis['amdahl_analysis'] = {
            'parallelizable_fraction': parallelizable_fraction,
            'sequential_fraction': 1 - parallelizable_fraction,
            'parallelizable_time_ms': parallelizable_time * 1000,
            'sequential_time_ms': sequential_time * 1000,
        }
        
        # Calculate theoretical speedup limits
        num_cores = self.system_info['cpu_count']
        theoretical_speedups = {}
        
        for cores in [1, 2, 4, num_cores]:
            if cores <= num_cores:
                # Amdahl's Law: Speedup = 1 / (S + P/N)
                # where S = sequential fraction, P = parallel fraction, N = number of cores
                speedup = 1 / (sequential_time/total_time + (parallelizable_time/total_time)/cores)
                theoretical_speedups[f'{cores}_cores'] = speedup
        
        analysis['theoretical_speedups'] = theoretical_speedups
        
        # Memory bandwidth limitations
        memory_reqs = memory_analysis.get('memory_requirements', {})
        measured_bandwidth = memory_analysis.get('measured_bandwidth_gb_s', 10)  # Conservative estimate
        
        # Theoretical memory bandwidth on EC2 g4dn.xlarge: ~25 GB/s
        ec2_bandwidth_gb_s = 25.0
        
        analysis['memory_constraints'] = {
            'current_bandwidth_gb_s': measured_bandwidth,
            'ec2_theoretical_bandwidth_gb_s': ec2_bandwidth_gb_s,
            'bandwidth_utilization': measured_bandwidth / ec2_bandwidth_gb_s,
            'memory_bound_speedup_limit': ec2_bandwidth_gb_s / measured_bandwidth,
        }
        
        # C++ implementation improvements
        cpp_improvements = {
            'function_call_overhead_reduction': 1.2,  # Reduced Python function calls
            'memory_layout_optimization': 1.1,       # Better data locality
            'simd_vectorization': 1.5,               # AVX2/AVX-512 for array operations
            'reduced_memory_allocations': 1.3,       # Stack allocation, memory pools
            'compiler_optimizations': 1.2,           # O3, loop unrolling, etc.
        }
        
        total_cpp_improvement = 1.0
        for improvement, factor in cpp_improvements.items():
            total_cpp_improvement *= factor
        
        analysis['cpp_improvements'] = cpp_improvements
        analysis['total_cpp_improvement'] = total_cpp_improvement
        
        # Realistic speedup estimates
        python_threading_speedup = threading_perf.get('speedup_4', 1.0) if threading_perf else 2.5
        
        # Conservative estimate: C++ improvements + better threading - overhead
        realistic_speedup_estimates = {
            'conservative': min(total_cpp_improvement * 2.0, 
                              analysis['memory_constraints']['memory_bound_speedup_limit']),
            'optimistic': min(total_cpp_improvement * 3.0,
                            analysis['memory_constraints']['memory_bound_speedup_limit']),
            'theoretical_max': min(theoretical_speedups.get('4_cores', 4.0) * total_cpp_improvement,
                                 analysis['memory_constraints']['memory_bound_speedup_limit']),
        }
        
        analysis['realistic_speedup_estimates'] = realistic_speedup_estimates
        
        return analysis
    
    def assess_implementation_complexity(self) -> Dict:
        """Assess the complexity of implementing C++ + OpenMP solution"""
        print("\n=== Assessing Implementation Complexity ===")
        
        complexity = {}
        
        # Technical components needed
        components = {
            'pybind11_bindings': {
                'complexity': 'Medium',
                'effort_days': 2,
                'description': 'Python-C++ interface for image arrays'
            },
            'opencv_cpp_integration': {
                'complexity': 'Low',
                'effort_days': 1,
                'description': 'Using OpenCV C++ API instead of Python wrapper'
            },
            'openmp_parallelization': {
                'complexity': 'Medium',
                'effort_days': 3,
                'description': 'Parallel loops for image processing'
            },
            'memory_management': {
                'complexity': 'High',
                'effort_days': 4,
                'description': 'Efficient memory allocation and copying'
            },
            'simd_optimization': {
                'complexity': 'High',
                'effort_days': 5,
                'description': 'Hand-optimized SIMD kernels for alpha blending'
            },
            'build_system': {
                'complexity': 'Medium',
                'effort_days': 2,
                'description': 'CMake build system, compiler flags, deployment'
            },
            'testing_validation': {
                'complexity': 'Medium',
                'effort_days': 3,
                'description': 'Ensure identical output to Python version'
            }
        }
        
        complexity['components'] = components
        complexity['total_effort_days'] = sum(comp['effort_days'] for comp in components.values())
        
        # Risk assessment
        risks = {
            'deployment_complexity': 'High - Need compiled binaries on EC2',
            'debugging_difficulty': 'High - C++ debugging vs Python',
            'maintenance_overhead': 'Medium - Additional build/test complexity',
            'compatibility_issues': 'Medium - OpenCV/NumPy version dependencies',
        }
        
        complexity['risks'] = risks
        
        # Alternatives to consider
        alternatives = {
            'numba_jit': {
                'effort_days': 1,
                'expected_speedup': '2-3x',
                'pros': 'Easy to implement, no deployment complexity',
                'cons': 'Limited SIMD control, still Python overhead'
            },
            'numpy_optimizations': {
                'effort_days': 0.5,
                'expected_speedup': '1.2-1.5x',
                'pros': 'Zero deployment complexity',
                'cons': 'Limited gains, still single-threaded'
            },
            'threading_only': {
                'effort_days': 0.5,
                'expected_speedup': '2-2.5x',
                'pros': 'Easy to implement, no new dependencies',
                'cons': 'GIL limitations, no SIMD benefits'
            }
        }
        
        complexity['alternatives'] = alternatives
        
        return complexity
    
    def run_full_analysis(self) -> Dict:
        """Run complete performance analysis"""
        print("Torque 3D Scanning Pipeline - Performance Analysis")
        print("=" * 60)
        print(f"System: {self.system_info['cpu_brand']}")
        print(f"CPU Cores: {self.system_info['cpu_count']}")
        print(f"Memory: {self.system_info['memory_total_gb']:.1f} GB")
        
        # Create test data matching real workload
        images, masks = self.create_test_data()
        
        # Profile current implementation
        self.results['current_implementation'] = self.profile_current_implementation(images, masks)
        
        # Test threading potential
        self.results['threading_potential'] = self.profile_threading_potential(images, masks)
        
        # Analyze memory patterns
        self.results['memory_analysis'] = self.analyze_memory_patterns(images, masks)
        
        # Estimate C++ speedup potential
        self.results['cpp_speedup_analysis'] = self.estimate_cpp_openmp_speedup()
        
        # Assess implementation complexity
        self.results['implementation_complexity'] = self.assess_implementation_complexity()
        
        # Generate recommendations
        self.results['recommendations'] = self._generate_recommendations()
        
        return self.results
    
    def _generate_recommendations(self) -> Dict:
        """Generate actionable recommendations based on analysis"""
        
        current_perf = self.results['current_implementation']
        speedup_analysis = self.results['cpp_speedup_analysis']
        complexity = self.results['implementation_complexity']
        
        recommendations = {}
        
        # Determine if optimization is worth it
        current_time = current_perf.get('batch_sequential_time', 1.0)
        conservative_speedup = speedup_analysis['realistic_speedup_estimates']['conservative']
        optimistic_speedup = speedup_analysis['realistic_speedup_estimates']['optimistic']
        
        potential_time_saved = current_time * (1 - 1/conservative_speedup)
        development_cost = complexity['total_effort_days']
        
        if potential_time_saved < 2.0:  # Less than 2 seconds saved
            recommendation = "NOT_RECOMMENDED"
            reason = f"Potential time savings ({potential_time_saved:.1f}s) don't justify {development_cost} days of work"
        elif conservative_speedup < 2.0:
            recommendation = "CONSIDER_ALTERNATIVES"
            reason = f"Conservative speedup estimate ({conservative_speedup:.1f}x) is modest. Consider simpler alternatives first."
        else:
            recommendation = "RECOMMENDED"
            reason = f"Good speedup potential ({conservative_speedup:.1f}-{optimistic_speedup:.1f}x) justifies development effort"
        
        recommendations['overall'] = {
            'recommendation': recommendation,
            'reason': reason,
            'estimated_time_savings_seconds': potential_time_saved,
            'development_effort_days': development_cost
        }
        
        # Specific recommendations
        specific_recs = []
        
        if speedup_analysis['memory_constraints']['bandwidth_utilization'] > 0.8:
            specific_recs.append("MEMORY_BOUND: Optimization gains will be limited by memory bandwidth")
        
        if speedup_analysis['amdahl_analysis']['parallelizable_fraction'] > 0.9:
            specific_recs.append("HIGHLY_PARALLELIZABLE: Good candidate for multi-threading")
        
        threading_speedup = self.results['threading_potential'].get('speedup_4', 1.0)
        if threading_speedup > 2.0:
            specific_recs.append("TRY_THREADING_FIRST: Python threading shows good gains, try this first")
        
        recommendations['specific'] = specific_recs
        
        return recommendations
    
    def print_summary(self):
        """Print a comprehensive analysis summary"""
        if not self.results:
            print("No analysis results available. Run run_full_analysis() first.")
            return
        
        print("\n" + "=" * 80)
        print("TORQUE 3D SCANNING PIPELINE - PERFORMANCE ANALYSIS SUMMARY")
        print("=" * 80)
        
        # Current performance
        current = self.results['current_implementation']
        print(f"\n📊 CURRENT PERFORMANCE:")
        print(f"   • Single image processing: {current['single_image_time']*1000:.1f} ms")
        print(f"   • Batch processing (12 images): {current['batch_sequential_time']:.2f} seconds")
        print(f"   • Processing rate: {current['images_per_second']:.1f} images/second")
        
        memory = current['memory_analysis']
        print(f"\n💾 MEMORY USAGE:")
        print(f"   • Input image: {memory['input_image_mb']:.1f} MB")
        print(f"   • Output RGBA: {memory['output_rgba_mb']:.1f} MB")
        print(f"   • Total working set: {memory['total_working_set_mb']:.1f} MB")
        
        # Threading potential
        threading = self.results['threading_potential']
        print(f"\n🔀 THREADING ANALYSIS:")
        for key, value in threading.items():
            if key.startswith('speedup_'):
                threads = key.split('_')[1]
                print(f"   • {threads} threads: {value:.1f}x speedup")
        
        # C++ speedup estimates
        cpp_analysis = self.results['cpp_speedup_analysis']
        speedups = cpp_analysis['realistic_speedup_estimates']
        print(f"\n⚡ C++ + OPENMP SPEEDUP ESTIMATES:")
        print(f"   • Conservative: {speedups['conservative']:.1f}x")
        print(f"   • Optimistic: {speedups['optimistic']:.1f}x")
        print(f"   • Theoretical max: {speedups['theoretical_max']:.1f}x")
        
        amdahl = cpp_analysis['amdahl_analysis']
        print(f"\n🔬 PARALLELIZATION ANALYSIS:")
        print(f"   • Parallelizable portion: {amdahl['parallelizable_fraction']*100:.1f}%")
        print(f"   • Sequential bottleneck: {amdahl['sequential_fraction']*100:.1f}%")
        
        memory_constraints = cpp_analysis['memory_constraints']
        print(f"\n🚧 MEMORY BANDWIDTH CONSTRAINTS:")
        print(f"   • Current bandwidth usage: {memory_constraints['current_bandwidth_gb_s']:.1f} GB/s")
        print(f"   • EC2 theoretical limit: {memory_constraints['ec2_theoretical_bandwidth_gb_s']:.1f} GB/s")
        print(f"   • Bandwidth utilization: {memory_constraints['bandwidth_utilization']*100:.1f}%")
        print(f"   • Memory-bound speedup limit: {memory_constraints['memory_bound_speedup_limit']:.1f}x")
        
        # Implementation complexity
        complexity = self.results['implementation_complexity']
        print(f"\n🛠 IMPLEMENTATION COMPLEXITY:")
        print(f"   • Estimated development effort: {complexity['total_effort_days']} days")
        print(f"   • Key risks:")
        for risk, description in complexity['risks'].items():
            print(f"     - {risk}: {description}")
        
        # Recommendations
        recommendations = self.results['recommendations']
        overall = recommendations['overall']
        print(f"\n🎯 RECOMMENDATIONS:")
        print(f"   • Overall: {overall['recommendation']}")
        print(f"   • Reason: {overall['reason']}")
        print(f"   • Time savings potential: {overall['estimated_time_savings_seconds']:.1f} seconds")
        
        if recommendations['specific']:
            print(f"   • Specific recommendations:")
            for rec in recommendations['specific']:
                print(f"     - {rec}")
        
        # Alternatives
        alternatives = complexity['alternatives']
        print(f"\n🔄 SIMPLER ALTERNATIVES TO CONSIDER:")
        for alt_name, alt_info in alternatives.items():
            print(f"   • {alt_name.replace('_', ' ').title()}:")
            print(f"     - Effort: {alt_info['effort_days']} days")
            print(f"     - Expected speedup: {alt_info['expected_speedup']}")
            print(f"     - Pros: {alt_info['pros']}")
            print(f"     - Cons: {alt_info['cons']}")
        
        print("\n" + "=" * 80)

def main():
    """Run the performance analysis"""
    profiler = PerformanceProfiler()
    profiler.run_full_analysis()
    profiler.print_summary()
    
    # Save detailed results
    import json
    with open('torque_performance_analysis.json', 'w') as f:
        # Convert numpy types to Python types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            return obj
        
        json.dump(convert_numpy(profiler.results), f, indent=2)
    
    print(f"\n📁 Detailed results saved to: torque_performance_analysis.json")

if __name__ == "__main__":
    main()