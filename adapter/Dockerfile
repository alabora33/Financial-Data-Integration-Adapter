# ── Aşama 1: Rust + maturin ile .so derle ──────────────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Rust toolchain kur
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install --no-cache-dir "maturin>=1.4,<2.0"

WORKDIR /build
COPY rust_engine/ .
# Python wheel (.whl) oluştur — içinde rust_validator.so var
RUN maturin build --release --interpreter python3.11

# ── Aşama 2: Hafif Python image, sadece wheel'i al ─────────────────────────
FROM python:3.11-slim
WORKDIR /app

COPY adapter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Rust'ın ürettiği wheel'i builder'dan al ve kur
COPY --from=builder /build/target/wheels/ /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY adapter/ .
