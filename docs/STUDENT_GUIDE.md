# GATE IGNITE - Student Examination Guide

Welcome to **GATE IGNITE**. This guide explains how to complete your online proctored examinations, undergo technical preflight diagnostics, navigate the secure exam engine, and view your published results.

---

## 1. Logging In & Available Exams (`/student`)
1. Log in using your institutional Clerk authentication credentials.
2. On your Student Dashboard, view **Available Exams**.
3. Click **Select Exam** to open the exam details and preflight screen.

---

## 2. Technical Preflight Diagnostics (`/student/exams/[examId]/preflight`)
Before starting an examination, the system runs automated preflight checks:
- **Online Network Connection**: Verifies backend server connectivity.
- **Server Time Synchronization**: Synchronizes client display timer with server timestamp.
- **Fullscreen API Support**: Checks browser compatibility for secure proctoring mode.

Review the exam rules notice, check **"I agree to exam rules"**, and click **Enter Secure Examination**.

---

## 3. Secure Exam Engine (`/exam/[examId]`)
- **Fullscreen Mode**: Browser fullscreen will be requested upon entry.
- **Synced Countdown Timer**: Displayed in the top bar. Time limits are enforced by server time.
- **Answering & Real-Time Autosave**: Click an option to select an answer. Inspect the save indicator (`Saving...`, `Saved`). Answers are saved atomically to the server.
- **Question Palette**: Toggle the palette to view Answered, Unanswered, Current, and Flagged questions.
- **Proctoring Warnings**: Do not switch tabs, minimize windows, exit fullscreen, copy text, or right click. Reaching the maximum warning limit will automatically terminate your examination session.
- **Submission**: Click **Submit Exam**, confirm your answered vs unanswered count, and finalize your attempt.

---

## 4. Viewing Results & Analytics (`/student/results`, `/student/analytics`)
- Once results are published by your administrator, open `/student/results` to view your score, percentage badge, pass/fail status, and question breakdown report.
- Open `/student/analytics` to view your performance trend timeline over time, subject strengths, and improvement areas.
