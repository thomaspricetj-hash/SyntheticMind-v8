// C:\Users\thomas price\Desktop\SyntheticMind-v8\bitdrop_core\ai\compression\src\lib.rs

use pyo3::prelude::*;
use pyo3::types::PyBytes;

use turbovec::TurboQuantIndex;

/// Python-facing TurboVec encoder:
///   encode(vectors: float32 buffer, dim: int, bit_width: int) -> bytes
/// The returned bytes are a `.tv` TurboVec index file (TVPI v3 format).
#[pyclass]
struct PyTurboVecEncoder {
    dim: usize,
    bit_width: usize,
}

#[pymethods]
impl PyTurboVecEncoder {
    #[new]
    fn new(dim: usize, bit_width: usize) -> PyResult<Self> {
        if !(2..=4).contains(&bit_width) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("bit_width must be 2, 3, or 4, got {bit_width}"),
            ));
        }
        if dim == 0 || dim % 8 != 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("dim must be a positive multiple of 8, got {dim}"),
            ));
        }
        Ok(Self { dim, bit_width })
    }

    /// Encode a flat f32 buffer of shape (n, dim) into a TurboVec `.tv` blob.
    ///
    /// `vectors` must be a contiguous float32 buffer (e.g. numpy array, memoryview).
    fn encode<'py>(&self, py: Python<'py>, vectors: &PyAny) -> PyResult<&'py PyBytes> {
        // Interpret as buffer
        let buf = vectors
            .buffer()
            .map_err(|e| pyo3::exceptions::PyTypeError::new_err(e.to_string()))?;
        if buf.item_size() != 4 {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "encode expects float32 buffer",
            ));
        }

        let len = buf.len_bytes() / 4;
        if len % self.dim != 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("buffer length {len} not multiple of dim {}", self.dim),
            ));
        }
        let n = len / self.dim;

        // SAFETY: contiguous float32 buffer
        let ptr = buf.as_contiguous().as_ptr() as *const f32;
        let slice = unsafe { std::slice::from_raw_parts(ptr, len) };

        // Build index and add vectors
        let mut index = TurboQuantIndex::new(self.dim, self.bit_width)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{e}")))?;
        index
            .add_2d(slice, self.dim)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{e}")))?;

        // Write to a temporary file, then read bytes back
        let tmp_path = std::env::temp_dir().join(format!(
            "turbovec_tmp_{}_{}.tv",
            self.dim, self.bit_width
        ));
        index
            .write(&tmp_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let tv_bytes = std::fs::read(&tmp_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let _ = std::fs::remove_file(&tmp_path);

        Ok(PyBytes::new(py, &tv_bytes))
    }
}

#[pymodule]
fn bitdrop_compression(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyTurboVecEncoder>()?;
    Ok(())
}
