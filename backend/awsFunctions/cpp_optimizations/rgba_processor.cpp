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
     * batch rgba processing with OpenMP + SIMD optimization
     * works with existing sam2_service.py workflow
     */
    static py::dict batch_create_rgba_optimized(
        // vector of img paths, not a dir
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
        
        // check masks array shape: (num_images, height, width)
        auto masks_buf = masks_array.request();
        if (masks_buf.ndim != 3 || masks_buf.shape[0] != num_images) {
            throw std::invalid_argument("Masks array must have shape (num_images, height, width)");
        }
        
        const int height = masks_buf.shape[1];
        const int width = masks_buf.shape[2];
        const uint8_t* masks_data = static_cast<const uint8_t*>(masks_buf.ptr);
        
        // thread-safe counters for stats
        std::atomic<int> processed{0};
        std::atomic<int> errors{0};
        std::vector<std::string> output_files(num_images);
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // limit threads to 4 for memory efficiency
        const int max_threads = std::min(4, static_cast<int>(std::thread::hardware_concurrency()));
        
        #ifdef _OPENMP
        omp_set_num_threads(max_threads);
        #endif
        
        // process images in parallel with OpenMP
        #pragma omp parallel for schedule(dynamic) shared(output_files)
        for (int i = 0; i < num_images; ++i) {
            try {
                // load image
                cv::Mat image = cv::imread(image_paths[i], cv::IMREAD_COLOR);
                if (image.empty()) {
                    printf("ERROR: Could not load image: %s\n", image_paths[i].c_str());
                    errors.fetch_add(1);
                    continue;
                }
                
                // check dimensions match mask
                if (image.rows != height || image.cols != width) {
                    printf("ERROR: Image dimensions (%dx%d) don't match mask (%dx%d): %s\n",
                           image.cols, image.rows, width, height, image_paths[i].c_str());
                    errors.fetch_add(1);
                    continue;
                }
                
                // convert BGR to RGB
                cv::Mat image_rgb;
                cv::cvtColor(image, image_rgb, cv::COLOR_BGR2RGB);
                
                // get mask data for this image
                const uint8_t* mask_data = masks_data + (static_cast<size_t>(i) * height * width);
                
                // create RGBA output with aligned memory
                cv::Mat rgba_image(height, width, CV_8UC4);
                
                // SIMD-optimized pixel processing
                const int total_pixels = height * width;
                uint8_t* __restrict__ rgba_ptr = rgba_image.ptr<uint8_t>();
                const uint8_t* __restrict__ rgb_ptr = image_rgb.ptr<uint8_t>();
                
                // vectorize with alignment hints for SIMD
                #pragma omp simd aligned(rgb_ptr, mask_data, rgba_ptr: 32) \
                                safelen(16) \
                                simdlen(8)
                for (int pixel = 0; pixel < total_pixels; ++pixel) {
                    const int rgb_offset = pixel * 3;
                    const int rgba_offset = pixel * 4;
                    
                    // copy RGB channels
                    rgba_ptr[rgba_offset + 0] = rgb_ptr[rgb_offset + 0]; // R
                    rgba_ptr[rgba_offset + 1] = rgb_ptr[rgb_offset + 1]; // G
                    rgba_ptr[rgba_offset + 2] = rgb_ptr[rgb_offset + 2]; // B
                    
                    // alpha channel (branchless for vectorization)
                    rgba_ptr[rgba_offset + 3] = (mask_data[pixel] > 0) ? 255 : 0; // A
                }
                
                // save with decent PNG compression
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
        
        // clean up empty entries
        std::vector<std::string> valid_output_files;
        for (const auto& file : output_files) {
            if (!file.empty()) {
                valid_output_files.push_back(file);
            }
        }
        
        // return stats matching python format
        py::dict results;
        results["processed"] = processed.load();
        results["errors"] = errors.load();
        results["output_files"] = valid_output_files;
        results["uploaded"] = 0;  // s3 handled in python
        
        // perf metrics for benchmarking
        results["processing_time_ms"] = processing_time_ms;
        results["avg_time_per_image_ms"] = processed.load() > 0 ? 
            processing_time_ms / processed.load() : 0.0;
        
        double total_pixels = processed.load() * height * width;
        double mpixels_per_sec = (total_pixels / 1e6) / (processing_time_ms / 1000.0);
        results["throughput_mpix_per_sec"] = mpixels_per_sec;
        results["threads_used"] = max_threads;
        
        printf("c++ OpenMP+SIMD rgba processing results:\n");
        printf("  processed: %d/%d images\n", processed.load(), num_images);
        printf("  errors: %d\n", errors.load());
        printf("  total time: %.2f ms (%.2f ms/image)\n", 
               processing_time_ms, 
               processed.load() > 0 ? processing_time_ms / processed.load() : 0.0);
        printf("  throughput: %.1f MPix/s\n", mpixels_per_sec);
        printf("  threads: %d\n", max_threads);
        
        return results;
    }
    
    /**
     * single image rgba processing (compatibility function)
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
            
            // single-threaded SIMD for one image
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
     * system info for checking optimization support
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
        
        // check what SIMD support we have
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
        
        // compiler optimization status
        #ifdef __OPTIMIZE__
        info["compiler_optimization"] = true;
        #else
        info["compiler_optimization"] = false;
        #endif
        
        return info;
    }
};

// python module definition
PYBIND11_MODULE(torque_cpp, m) {
    m.doc() = "c++ optimizations for torque 3d scanning pipeline using OpenMP + SIMD";
    
    py::class_<RGBAProcessor>(m, "RGBAProcessor")
        .def_static("batch_create_rgba", &RGBAProcessor::batch_create_rgba_optimized,
                   "batch rgba processing with OpenMP parallelization and SIMD vectorization")
        .def_static("create_rgba_single", &RGBAProcessor::create_rgba_single,
                   "single image rgba processing with SIMD optimization")
        .def_static("get_info", &RGBAProcessor::get_optimization_info,
                   "get system optimization capabilities and compiler information");
    
    // convenience functions for direct access
    m.def("batch_rgba", &RGBAProcessor::batch_create_rgba_optimized,
          "high-performance batch rgba processing");
    m.def("single_rgba", &RGBAProcessor::create_rgba_single,
          "single image rgba processing");
    m.def("optimization_info", &RGBAProcessor::get_optimization_info,
          "system and compiler optimization information");
}