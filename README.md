[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/pDzzm9hi)
# Take-Home Interview — Backend (Django)

## Context
Portal is an application where event organizers create and manage **live event programs** (schedules / agendas). Programs can be updated even after being shared publicly.

The backend is responsible for program structure, validation, and exposing clear program state to the frontend.

---

## Task
Build a small Django backend (API-first) that supports:

- Creating and editing event programs
- Adding and editing program items
- Representing some notion of **program state or readiness**
- Sharing a program externally

You decide:
- The data model
- The API endpoints
- What “ready to share” means
- Whether state is stored or derived
- How sharing works technically
- What validations are important

There is no single correct solution.

---

## Requirements
- Django + Django REST Framework
- A REST API (no templates required)
- At least one endpoint that returns a **program overview** suitable for a dashboard view
- Basic automated tests (focus on important behavior)

---

## README Expectations
Your `README.md` should include:

- How to run the project locally
- Any assumptions you made
- Key design decisions
- Tradeoffs you consciously chose
- What you would improve or extend with more time

Keep explanations concise and technical.

---

## Constraints
- Keep the scope intentionally small
- Optimize for clarity, correctness, and maintainability
- Avoid unnecessary abstractions

---

## What We Evaluate
- Data modeling and API design
- Validation and edge-case handling
- Code structure and separation of concerns
- Test intent and coverage quality
- Engineering judgment and tradeoffs

---

## Submission
- Complete the assignment using ** Github Classroom**
- Push all work to the provided repository
- Do not include external credentials or secrets
