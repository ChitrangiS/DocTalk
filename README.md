# DocTalk AI 

> **Chat with your documents using AI. Get accurate, source-grounded answers instead of manually searching hundreds of pages.**

**🌐 Live Demo:** https://doc-talk-theta.vercel.app/

---

## Overview

DocTalk AI is a full-stack Retrieval-Augmented Generation (RAG) application that enables users to interact with documents through natural language. Upload a PDF, ask questions, and receive context-aware answers generated from the document itself instead of the model's memory.

Unlike traditional PDF readers, DocTalk performs semantic search over document embeddings, retrieves the most relevant passages, and uses an LLM to generate grounded responses with minimal hallucination.

The project was built to demonstrate production-level AI engineering concepts including document ingestion, vector search, retrieval pipelines, streaming responses, and scalable backend architecture.

---

## Features

* 📄 Upload PDF documents
* 💬 Natural language conversations with documents
* 🔍 Semantic search using vector embeddings
* 🧠 Retrieval-Augmented Generation (RAG)
* ⚡ Real-time streaming AI responses
* 📚 Context-aware multi-turn conversations
* 🚀 Optimized for large documents
* 🎯 Reduced hallucinations through retrieval
* 📱 Responsive modern UI
* 🔒 Secure backend architecture

---

## Tech Stack

### Frontend

* Next.js 14
* React
* TypeScript
* Tailwind CSS

### Backend

* FastAPI
* Python
* Uvicorn

### AI Stack

* Llama 3.1 (Groq)
* BAAI/BGE Embedding Model
* ChromaDB Vector Database
* Retrieval-Augmented Generation (RAG)

### Deployment

* Frontend: Vercel
* Backend: FastAPI

---

# System Architecture

```text
                User
                  │
                  ▼
         Next.js Frontend
                  │
                  ▼
          FastAPI Backend
                  │
     ┌────────────┴────────────┐
     │                         │
     ▼                         ▼
PDF Upload              User Question
     │                         │
     ▼                         ▼
Text Extraction         Embed Query
     │                         │
     ▼                         ▼
Document Chunking       Semantic Search
     │                         │
     ▼                         ▼
Generate Embeddings ◄── ChromaDB
     │                         │
     └────────────┬────────────┘
                  ▼
        Retrieved Context
                  │
                  ▼
        Llama 3.1 (Groq)
                  │
                  ▼
     Streaming AI Response
                  │
                  ▼
             User Interface
```

---

## RAG Pipeline

```text
Upload PDF
      │
      ▼
Extract Text
      │
      ▼
Chunk Document
      │
      ▼
Generate Embeddings
      │
      ▼
Store in ChromaDB
      │
      ▼
User Query
      │
      ▼
Embed Query
      │
      ▼
Similarity Search
      │
      ▼
Retrieve Top-k Chunks
      │
      ▼
LLM Generation
      │
      ▼
Grounded Response
```

---

## Why RAG?

Large Language Models cannot reliably answer questions about documents they have never seen.

DocTalk solves this by:

* Retrieving only the most relevant document sections
* Injecting retrieved context into the LLM prompt
* Generating answers grounded in document content
* Significantly reducing hallucinations
* Improving factual accuracy

---

## Engineering Highlights

* Implemented a production-style RAG pipeline for document intelligence.
* Optimized retrieval using dense vector embeddings and semantic similarity search.
* Designed a modular FastAPI backend separating ingestion, retrieval, and generation.
* Streamed LLM responses for lower perceived latency.
* Built a responsive Next.js interface for a seamless chat experience.
* Structured the application for easy replacement of embedding models, vector databases, or LLM providers.

---

## Challenges Solved

* Efficient processing of long PDF documents
* Maintaining retrieval accuracy across hundreds of pages
* Preventing hallucinations using retrieval grounding
* Managing conversation context across multiple queries
* Delivering low-latency AI responses through streaming

---

## Future Improvements

* Support for DOCX, PPTX, and TXT files
* OCR for scanned PDFs
* Citation highlighting
* Multi-document chat
* Conversation memory
* Hybrid keyword + semantic search
* Authentication and user workspaces
* Document summarization
* Voice-based document interaction

---

## Learning Outcomes

This project strengthened my understanding of:

* Retrieval-Augmented Generation (RAG)
* Vector Databases
* Embedding Models
* Semantic Search
* FastAPI Backend Development
* Full-Stack AI Application Development
* LLM Integration
* API Design
* Production Deployment
* AI System Architecture

---

## Project Goal

The objective of DocTalk AI is to build an intelligent document assistant capable of understanding large documents and answering questions with context-aware, retrieval-grounded responses. Rather than showcasing prompt engineering alone, the project demonstrates the complete lifecycle of an AI application—from document ingestion and vector indexing to retrieval, generation, and deployment.

---

## Live Demo

https://doc-talk-theta.vercel.app/

If you found this project interesting, feel free to ⭐ the repository.
