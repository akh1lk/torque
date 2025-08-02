#include <opencv2/opencv.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/imgcodecs.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <vector>
#include <string>
#include <chrono>
#include <atomic>
#include <thread>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

class RGBAProcessor {
public:
    /**
     * High-performance batch RGBA processing using OpenMP + SIMD optimization
     * Designed to integrate seamlessly with existing sam2_service.py workflow
     */
    static py::dict batch_create_rgba_optimized(
        const std::vector<std::string>& image_paths,
        const py::array_t<uint8_t>& masks_array,
        const std::vector<std::string>& output_paths
    ) {
        const int num_images = image_paths.size();
        
        if (num_images == 0) {
            throw std::invalid_argument("No images provided");
        }
        if (num_images != output_paths.size()) {
            throw std::invalid_argument("Number of image paths must match output paths");
        }
        
        // Validate masks array shape: (num_images, height, width)
        auto masks_buf = masks_array.request();
        if (masks_buf.ndim != 3 || masks_buf.shape[0] != num_images) {
            throw std::invalid_argument("Masks array must have shape (num_images, height, width)");
        }
        
        const int height = masks_buf.shape[1];
        const int width = masks_buf.shape[2];
        const uint8_t* masks_data = static_cast<const uint8_t*>(masks_buf.ptr);
        
        // Processing statistics (thread-safe)
        std::atomic<int> processed{0};
        std::atomic<int> errors{0};
        std::vector<std::string> output_files(num_images);
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Set optimal thread count (limit to 4 for memory efficiency)
        const int max_threads = std::min(4, static_cast<int>(std::thread::hardware_concurrency()));
        
        #ifdef _OPENMP
        omp_set_num_threads(max_threads);
        #endif
        
        // Process images in parallel using OpenMP
        #pragma omp parallel for schedule(dynamic) shared(output_files)
        for (int i = 0; i < num_images; ++i) {
            try {
                // Load image
                cv::Mat image = cv::imread(image_paths[i], cv::IMREAD_COLOR);
                if (image.empty()) {
                    printf("ERROR: Could not load image: %s\n", image_paths[i].c_str());
                    errors.fetch_add(1);
                    continue;
                }
                
                // Validate dimensions
                if (image.rows != height || image.cols != width) {
                    printf("ERROR: Image dimensions (%dx%d) don't match mask (%dx%d): %s\n",
                           image.cols, image.rows, width, height, image_paths[i].c_str());
                    errors.fetch_add(1);
                    continue;
                }
                
                // Convert BGR to RGB
                cv::Mat image_rgb;
                cv::cvtColor(image, image_rgb, cv::COLOR_BGR2RGB);
                
                // Get mask data for this image
                const uint8_t* mask_data = masks_data + (static_cast<size_t>(i) * height * width);
                
                // Create RGBA output with optimized memory layout
                cv::Mat rgba_image(height, width, CV_8UC4);
                
                // High-performance SIMD-optimized pixel processing
                const int total_pixels = height * width;
                uint8_t* __restrict__ rgba_ptr = rgba_image.ptr<uint8_t>();
                const uint8_t* __restrict__ rgb_ptr = image_rgb.ptr<uint8_t>();
                
                // SIMD vectorization with explicit alignment hints
                #pragma omp simd aligned(rgb_ptr, mask_data, rgba_ptr: 32) \
                                safelen(16) \
                                simdlen(8)
                for (int pixel = 0; pixel < total_pixels; ++pixel) {
                    const int rgb_offset = pixel * 3;
                    const int rgba_offset = pixel * 4;
                    
                    // Optimized memory access pattern - copy RGB channels
                    rgba_ptr[rgba_offset + 0] = rgb_ptr[rgb_offset + 0]; // R
                    rgba_ptr[rgba_offset + 1] = rgb_ptr[rgb_offset + 1]; // G
                    rgba_ptr[rgba_offset + 2] = rgb_ptr[rgb_offset + 2]; // B
                    
                    // Generate alpha channel (branchless, vectorizable)
                    rgba_ptr[rgba_offset + 3] = (mask_data[pixel] > 0) ? 255 : 0; // A
                }
                
                // Save RGBA image with optimized PNG compression
                std::vector<int> png_params = {cv::IMWRITE_PNG_COMPRESSION, 6};
                if (cv::imwrite(output_paths[i], rgba_image, png_params)) {
                    output_files[i] = output_paths[i];
                    processed.fetch_add(1);
                } else {
                    printf("ERROR: Could not save RGBA image: %s\n", output_paths[i].c_str());
                    errors.fetch_add(1);
                }
                
            } catch (const std::exception& e) {
                printf("ERROR: Exception processing image %d: %s\n", i, e.what());
                errors.fetch_add(1);
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        double processing_time_ms = duration.count() / 1000.0;
        
        // Filter out empty strings from output_files
        std::vector<std::string> valid_output_files;
        for (const auto& file : output_files) {
            if (!file.empty()) {
                valid_output_files.push_back(file);
            }
        }
        
        // Create return statistics (matches Python sam2_service.py format exactly)
        py::dict results;
        results["processed"] = processed.load();
        results["errors"] = errors.load();
        results["output_files"] = valid_output_files;
        results["uploaded"] = 0;  // S3 upload handled separately in Python
        
        // Performance diagnostics for optimization tracking
        results["processing_time_ms"] = processing_time_ms;
        results["avg_time_per_image_ms"] = processed.load() > 0 ? 
            processing_time_ms / processed.load() : 0.0;
        
        double total_pixels = processed.load() * height * width;
        double mpixels_per_sec = (total_pixels / 1e6) / (processing_time_ms / 1000.0);
        results["throughput_mpix_per_sec"] = mpixels_per_sec;
        results["threads_used"] = max_threads;
        
        printf("C++ OpenMP+SIMD RGBA Processing Results:\n");
        printf("  ✅ Processed: %d/%d images\n", processed.load(), num_images);
        printf("  ❌ Errors: %d\n", errors.load());
        printf("  ⏱️  Total time: %.2f ms (%.2f ms/image)\n", 
               processing_time_ms, 
               processed.load() > 0 ? processing_time_ms / processed.load() : 0.0);
        printf("  🚀 Throughput: %.1f MPix/s\n", mpixels_per_sec);
        printf("  🧵 Threads: %d\n", max_threads);
        
        return results;
    }
    
    /**
     * Single image RGBA processing (for compatibility with existing code)
     */
    static bool create_rgba_single(
        const std::string& image_path,
        const py::array_t<uint8_t>& mask,
        const std::string& output_path
    ) {
        try {
            // Load image
            cv::Mat image = cv::imread(image_path, cv::IMREAD_COLOR);
            if (image.empty()) {
                return false;
            }
            
            // Get mask data
            auto mask_buf = mask.request();
            if (mask_buf.ndim != 2) {
                throw std::invalid_argument("Mask must be 2D array");
            }
            
            const int height = mask_buf.shape[0];
            const int width = mask_buf.shape[1];
            const uint8_t* mask_data = static_cast<const uint8_t*>(mask_buf.ptr);
            
            // Validate dimensions
            if (image.rows != height || image.cols != width) {
                return false;
            }
            
            // Convert and process
            cv::Mat image_rgb;
            cv::cvtColor(image, image_rgb, cv::COLOR_BGR2RGB);
            
            cv::Mat rgba_image(height, width, CV_8UC4);
            const int total_pixels = height * width;
            
            uint8_t* rgba_ptr = rgba_image.ptr<uint8_t>();
            const uint8_t* rgb_ptr = image_rgb.ptr<uint8_t>();
            
            // Single-threaded SIMD for single image
            #pragma omp simd aligned(rgb_ptr, mask_data, rgba_ptr: 32)
            for (int pixel = 0; pixel < total_pixels; ++pixel) {
                const int rgb_offset = pixel * 3;
                const int rgba_offset = pixel * 4;
                
                rgba_ptr[rgba_offset + 0] = rgb_ptr[rgb_offset + 0];
                rgba_ptr[rgba_offset + 1] = rgb_ptr[rgb_offset + 1];
                rgba_ptr[rgba_offset + 2] = rgb_ptr[rgb_offset + 2];
                rgba_ptr[rgba_offset + 3] = (mask_data[pixel] > 0) ? 255 : 0;
            }
            
            // Save with PNG compression
            std::vector<int> png_params = {cv::IMWRITE_PNG_COMPRESSION, 6};
            return cv::imwrite(output_path, rgba_image, png_params);
            
        } catch (const std::exception& e) {
            return false;
        }
    }
    
    /**
     * System information for optimization verification
     */
    static py::dict get_optimization_info() {
        py::dict info;
        
        #ifdef _OPENMP
        info["openmp_enabled"] = true;
        info["omp_max_threads"] = omp_get_max_threads();
        info["omp_num_procs"] = omp_get_num_procs();
        info["openmp_version"] = _OPENMP;
        #else
        info["openmp_enabled"] = false;
        info["omp_max_threads"] = 1;
        #endif
        
        info["hardware_concurrency"] = static_cast<int>(std::thread::hardware_concurrency());
        
        // SIMD capability detection
        #ifdef __AVX512F__
        info["simd_level"] = "AVX-512";
        #elif __AVX2__
        info["simd_level"] = "AVX2";
        #elif __AVX__
        info["simd_level"] = "AVX";
        #elif __SSE4_2__
        info["simd_level"] = "SSE4.2";
        #else
        info["simd_level"] = "basic";
        #endif
        
        // Compiler optimization flags
        #ifdef __OPTIMIZE__
        info["compiler_optimization"] = true;
        #else
        info["compiler_optimization"] = false;
        #endif
        
        return info;
    }
};

// Python module definition
PYBIND11_MODULE(torque_cpp, m) {
    m.doc() = "High-performance C++ optimizations for Torque 3D scanning pipeline using OpenMP + SIMD";
    
    py::class_<RGBAProcessor>(m, "RGBAProcessor")
        .def_static("batch_create_rgba", &RGBAProcessor::batch_create_rgba_optimized,
                   "Batch RGBA processing with OpenMP parallelization and SIMD vectorization")
        .def_static("create_rgba_single", &RGBAProcessor::create_rgba_single,
                   "Single image RGBA processing with SIMD optimization")
        .def_static("get_info", &RGBAProcessor::get_optimization_info,
                   "Get system optimization capabilities and compiler information");
    
    // Convenience functions for direct access
    m.def("batch_rgba", &RGBAProcessor::batch_create_rgba_optimized,
          "High-performance batch RGBA processing");
    m.def("single_rgba", &RGBAProcessor::create_rgba_single,
          "Single image RGBA processing");
    m.def("optimization_info", &RGBAProcessor::get_optimization_info,
          "System and compiler optimization information");
}