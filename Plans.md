# Plans.md: ToxiGuard-AI Development Roadmap

## Phase 1: Harness & Environment Sync [WIP]
- [x] Task 1.1: Initialize `CLAUDE.md` 65-line harness. | DoD: File exists in root. | Status: cc:완료
- [x] Task 1.2: Synchronize ToxiGuard-AI regulatory engine with Antigravity Project. | DoD: `ASHBY_ALERTS` and impurity logic imported/verified. | Status: cc:완료 [5f1a3e]
- [x] Task 1.3: Establish automated TDD pipeline for regulatory compliance. | DoD: Test script passes for standard genotoxicity alerts. | Status: cc:완료 [h8b9c2]

## Phase 2: Regulatory Engine Enhancement
- [x] Task 2.1: Integrate ICH M7 Class 1-5 categorization logic. | DoD: API returns correct classification for known impurities. | Status: cc:완료 [a3b7c9]
- [x] Task 2.2: Implement proactive degradation pathway simulation using RDKit. | DoD: Predicts standard degradation products for Atorvastatin. | Status: cc:완료 [e7d8f2]
- [x] Task 2.3: Implement harnessed evidence package and worker-report validation. | DoD: `worker-report.v1` is generated with R01-R13 validation gates and Evidence/QSAR traceability. | Status: cc:완료 [harness-v1]

## Phase 3: Reporting & Automation
- [ ] Task 3.1: Automate daily regulatory brief generation to Blogger. | DoD: `cron.js` successfully posts a validated toxicological report. | Status: cc:TODO
- [ ] Task 3.2: Final verification and submission-ready UI polish. | DoD: Glassmorphism UI displays real-time assessment status. | Status: cc:TODO
