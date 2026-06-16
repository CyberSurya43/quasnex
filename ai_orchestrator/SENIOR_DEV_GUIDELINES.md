# Senior Software Developer Guidelines

## Overview

This document describes the professional development tools, rules, and best practices embedded into the AI Orchestrator agents to ensure high-quality, production-ready code.

## Agent Enhancements

### Professional Guidelines Integration

Every agent now receives:

1. **Code Quality Standards** - Clean code principles, DRY, SOLID
2. **Security Best Practices** - Input validation, auth, data protection
3. **Testing Strategy** - Test pyramid, 80%+ coverage, edge cases
4. **Performance Guidelines** - Optimization, caching, profiling
5. **Documentation Standards** - API docs, inline comments, README

### Stage-Specific Rules

Each orchestration stage includes:

#### Frontend (Gemini)
- Responsive design (mobile-first)
- Accessibility (WCAG 2.1 AA)
- Performance optimization
- Component reusability
- Browser compatibility
- State management best practices

#### Backend (Codex)
- RESTful API design
- Database normalization
- Transaction management
- Proper error handling
- Structured logging
- Dependency injection

#### Testing (Codex)
- Unit tests (70%)
- Integration tests (20%)
- E2E tests (10%)
- Edge case coverage
- Mock external dependencies
- Test independence

#### Deployment (Codex)
- Multi-stage Docker builds
- Health checks
- Environment variables
- Secrets management
- Monitoring setup
- Rollback procedures

## Checklists Included

### Code Review Checklist
- ✓ Follows project style guide
- ✓ No hardcoded secrets
- ✓ Error handling implemented
- ✓ Tests included and passing
- ✓ No debug code
- ✓ Dependencies updated
- ✓ Security vulnerabilities checked
- ✓ Performance considered
- ✓ Documentation updated

### Security Checklist
- ✓ No hardcoded secrets
- ✓ Input validation
- ✓ SQL injection prevention
- ✓ XSS prevention
- ✓ CSRF protection
- ✓ Rate limiting
- ✓ HTTPS enforced
- ✓ Authentication proper
- ✓ Authorization in place
- ✓ Dependencies scanned
- ✓ Security headers configured
- ✓ Sensitive data encrypted

### Testing Checklist
- ✓ Unit tests for business logic
- ✓ Integration tests for APIs
- ✓ E2E tests for critical flows
- ✓ Edge cases tested
- ✓ Error conditions tested
- ✓ Security scenarios tested
- ✓ Performance benchmarks
- ✓ Tests independent
- ✓ Test data cleanup
- ✓ Mocks for external deps

### Deployment Checklist
- ✓ Environment variables documented
- ✓ Database migrations tested
- ✓ Rollback plan documented
- ✓ Health checks implemented
- ✓ Logging configured
- ✓ Monitoring set up
- ✓ Security scan passed
- ✓ Load testing completed
- ✓ Documentation updated
- ✓ Secrets rotated

## Agent-Specific Instructions

### Codex (Orchestrator, Backend, Testing, Deployment)

**Responsibilities:**
- Architecture design with scalability in mind
- Clean, testable backend code
- Comprehensive test coverage
- Production-ready deployment setup
- Security-first approach

**Standards:**
- RESTful or GraphQL best practices
- Repository pattern for data access
- Middleware for cross-cutting concerns
- Structured logging with context
- 12-factor app principles

### Gemini (Frontend)

**Responsibilities:**
- Pixel-perfect responsive layouts
- Accessible, keyboard-navigable UI
- Optimized performance
- Reusable components
- Error boundary handling

**Standards:**
- Mobile-first design (375px+)
- WCAG 2.1 AA compliance
- Code splitting and lazy loading
- Semantic HTML
- Proper state management

## Professional Tools

### Git Commit Standards
```
<type>: <subject> (max 50 chars)

<body> (optional, wrap at 72 chars)

<footer> (optional)

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- test: Adding tests
- docs: Documentation
- chore: Maintenance
- perf: Performance improvement
```

### Project Structure

**Backend:**
```
src/
  api/
  core/
  models/
  services/
  utils/
tests/
  unit/
  integration/
config/
docs/
.env.example
Dockerfile
```

**Frontend:**
```
src/
  components/
  pages/
  hooks/
  services/
  utils/
  styles/
  types/
tests/
public/
.env.example
```

## Quality Metrics

### Code Coverage
- Minimum: 80% for critical paths
- Unit tests: 70% of test suite
- Integration tests: 20% of test suite
- E2E tests: 10% of test suite

### Performance
- API response: < 200ms (p95)
- Page load: < 3s (LCP)
- Time to Interactive: < 5s
- Bundle size: < 200KB gzipped

### Security
- All inputs validated
- All outputs escaped
- No known vulnerabilities
- HTTPS enforced
- Security headers configured

## Continuous Improvement

Each agent completion note includes:
- Files created/modified
- Commands to run
- Known issues
- Next steps
- Recommendations for improvement

This ensures continuous learning and quality improvement across orchestration cycles.
