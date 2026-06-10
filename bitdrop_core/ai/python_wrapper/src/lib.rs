use pyo3::prelude::*;
use turbovec::TurboQuantIndex;
use std::fs::File;
use std::io::{Read, Write};
use std::path::PathBuf;

#[pyclass]
struct PyTurboVecEncoder {
    dim: usize,
    bit_width: usize,
    index: TurboQuantIndex,
}

#[pymethods]
impl PyTurboVecEncoder {
    #[new]
    fn new(dim: usize, bit_width: usize) -> PyResult<Self> {
        let index = TurboQuantIndex::new(dim, bit_width)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("{e}")))?;

        Ok(Self { dim, bit_width, index })
    }

    /// Encode vectors and return the TurboVec index file as bytes
    fn encode(&mut self, vectors: Vec<Vec<f32>>) -> PyResult<Vec<u8>> {
        // Flatten vectors
        let mut flat: Vec<f32> = Vec::with_capacity(vectors.len() * self.dim);

        for v in &vectors {
            if v.len() != self.dim {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Vector length {} != dim {}", v.len(), self.dim),
                ));
            }
            flat.extend_from_slice(v);
        }

        // Add vectors
        self.index.add(&flat);

        // Write to a temporary file
        let path = PathBuf::from("tq_temp_index.tv");
        self.index
            .write(&path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("{e}")))?;

        // Read file back into memory
        let mut file = File::open(&path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("{e}")))?;

        let mut buf = Vec::new();
        file.read_to_end(&mut buf)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("{e}")))?;

        // Remove the temp file
        let _ = std::fs::remove_file(&path);

        Ok(buf)
    }
}

#[pymodule]
fn python_wrapper(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyTurboVecEncoder>()?;
    Ok(())
}



