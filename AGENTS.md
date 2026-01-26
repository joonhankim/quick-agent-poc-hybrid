# Project Agent Guidelines

## 1. Project Overview
This project implements a chat system.

Main features:
- List chat rooms for a user
- Fetch messages for a selected chat room
- Pagination is required for all list APIs
- Database: PostgreSQL
- Backend only (no frontend implementation here)

## 2. Tech Stack
- Language: TypeScript
- Framework: Node.js + Fastify
- Database: PostgreSQL
- ORM: Prisma
- Migration: Prisma Migrate

## 3. Database Rules
- All tables must use `uuid` as primary key
- Timestamps:
  - `created_at` (required)
  - `updated_at` (required)
- Message ordering:
  - Messages are ordered by `created_at ASC`
- Pagination:
  - Use cursor-based pagination (no OFFSET)
- Indexing:
  - `chat_room_id + created_at` composite index is required

## 4. API Design Rules
- REST style
- List endpoints must support:
  - `limit`
  - `cursor`
- Do NOT expose internal IDs that are not required
- Validate user ownership of chat rooms

## 5. Implementation Policy
- Do NOT implement frontend code
- Do NOT add WebSocket logic
- Implement in the following order:
  1. Database schema
  2. Migration
  3. Repository layer
  4. Service layer
  5. API handlers
  6. Minimal tests

## 6. Safety Rules
- Any destructive DB change must be explained before execution
- Ask for confirmation before:
  - Running migrations
  - Writing production SQL
  - Deleting data

## 7. Communication Style
- Always explain:
  - Why a design choice was made
  - Trade-offs
- Show SQL / Prisma schema explicitly
- Ask before proceeding to the next major step
