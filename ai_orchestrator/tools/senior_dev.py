"""Senior Software Developer Tools and Rules for AI Agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DevelopmentRules:
    """Professional development rules and best practices."""
    
    # Code Quality Rules
    CODE_QUALITY = """
## Code Quality Standards

### General Principles
- Write self-documenting code with clear variable and function names
- Follow DRY (Don't Repeat Yourself) principle
- Keep functions small and focused (single responsibility)
- Use meaningful comments only when code intent isn't obvious
- Prefer composition over inheritance
- Handle errors explicitly, never silently fail

### Code Organization
- Group related functionality into modules
- Separate concerns (business logic, data access, presentation)
- Use consistent file and folder naming conventions
- Keep configuration separate from code
- Version control everything except secrets and generated files

### Performance
- Optimize for readability first, performance second
- Profile before optimizing
- Use appropriate data structures
- Avoid premature optimization
- Cache expensive operations when appropriate
"""

    # Security Best Practices
    SECURITY = """
## Security Best Practices

### Authentication & Authorization
- Never store passwords in plain text (use bcrypt, argon2)
- Implement proper session management
- Use JWT tokens with appropriate expiration
- Validate all user inputs on server side
- Implement rate limiting on sensitive endpoints

### Data Protection
- Never commit secrets, API keys, or credentials
- Use environment variables for sensitive config
- Sanitize all database inputs (prevent SQL injection)
- Escape output to prevent XSS attacks
- Use HTTPS for all production traffic
- Implement CORS properly

### API Security
- Validate and sanitize all API inputs
- Use parameterized queries or ORMs
- Implement proper error handling (don't leak stack traces)
- Log security events
- Keep dependencies updated
"""

    # Testing Strategy
    TESTING = """
## Testing Strategy

### Test Pyramid
- Unit Tests (70%): Test individual functions/methods
- Integration Tests (20%): Test component interactions
- E2E Tests (10%): Test critical user flows

### Test Best Practices
- Write tests before fixing bugs (TDD)
- Test edge cases and error conditions
- Use meaningful test names (describe what's being tested)
- Keep tests independent and isolated
- Mock external dependencies
- Aim for 80%+ code coverage on critical paths

### Test Organization
- Mirror source code structure in test files
- Use setup/teardown for test data
- Group related tests
- Keep tests fast and reliable
"""

    # Frontend Best Practices
    FRONTEND = """
## Frontend Best Practices

### Component Design
- Keep components small and reusable
- Use prop validation/TypeScript types
- Implement proper error boundaries
- Follow accessibility guidelines (WCAG 2.1 AA)
- Use semantic HTML

### State Management
- Keep state as local as possible
- Use proper state management for global state
- Avoid prop drilling
- Implement optimistic UI updates
- Handle loading and error states

### Performance
- Code splitting for large apps
- Lazy load components and routes
- Optimize images (WebP, lazy loading)
- Minimize bundle size
- Use production builds for deployment

### Accessibility
- All interactive elements keyboard accessible
- Proper ARIA labels and roles
- Color contrast meets WCAG standards
- Screen reader tested
- Focus management
"""

    # Backend Best Practices
    BACKEND = """
## Backend Best Practices

### API Design
- Use RESTful conventions or GraphQL best practices
- Version your APIs (v1, v2)
- Return appropriate HTTP status codes
- Implement pagination for list endpoints
- Document APIs (OpenAPI/Swagger)

### Database
- Use migrations for schema changes
- Index frequently queried fields
- Normalize data appropriately
- Use transactions for multi-step operations
- Implement soft deletes for important data

### Architecture
- Separate business logic from HTTP handlers
- Use dependency injection
- Implement repository pattern for data access
- Use middleware for cross-cutting concerns
- Follow 12-factor app principles

### Error Handling
- Use structured logging
- Return consistent error formats
- Log errors with context
- Implement retry logic for transient failures
- Use circuit breakers for external services
"""

    # Deployment Best Practices
    DEPLOYMENT = """
## Deployment Best Practices

### Containerization
- Use multi-stage Docker builds
- Minimize image size
- Run containers as non-root user
- Use specific version tags (not 'latest')
- Implement health checks

### CI/CD
- Automate tests in pipeline
- Run security scans
- Use blue-green or canary deployments
- Implement automatic rollback
- Version all releases

### Monitoring
- Implement logging (structured JSON logs)
- Add metrics and monitoring
- Set up alerts for critical issues
- Track error rates and response times
- Use distributed tracing for microservices

### Environment Management
- Use environment variables for config
- Never commit secrets
- Use secrets management (Vault, AWS Secrets Manager)
- Separate dev/staging/production environments
- Document environment setup
"""


class DevelopmentTools:
    """Tools for professional software development."""
    
    @staticmethod
    def get_code_review_checklist() -> list[str]:
        """Get code review checklist."""
        return [
            "Code follows project style guide",
            "No hardcoded secrets or credentials",
            "Error handling is implemented",
            "Tests are included and passing",
            "No unnecessary comments (code is self-documenting)",
            "No debug code or console.log statements",
            "Dependencies are up to date",
            "Security vulnerabilities checked",
            "Performance implications considered",
            "Documentation updated if needed",
        ]
    
    @staticmethod
    def get_git_commit_template() -> str:
        """Get professional git commit message template."""
        return """
# <type>: <subject> (max 50 chars)
# |<----  Using a Maximum Of 50 Characters  ---->|

# <body> (optional, wrap at 72 chars)
# |<----   Try To Limit Each Line to a Maximum Of 72 Characters   ---->|

# <footer> (optional)

# Type:
#   feat     (new feature)
#   fix      (bug fix)
#   docs     (documentation)
#   style    (formatting, missing semicolons, etc)
#   refactor (code change that neither fixes a bug nor adds a feature)
#   test     (adding missing tests)
#   chore    (maintain, dependencies update)
#   perf     (performance improvement)
#   ci       (CI/CD changes)
#   build    (build system changes)
"""
    
    @staticmethod
    def get_project_structure_template(project_type: str) -> dict[str, list[str]]:
        """Get recommended project structure."""
        templates = {
            "backend": [
                "src/",
                "src/api/",
                "src/core/",
                "src/models/",
                "src/services/",
                "src/utils/",
                "tests/",
                "tests/unit/",
                "tests/integration/",
                "config/",
                "scripts/",
                "docs/",
                ".env.example",
                "requirements.txt or package.json",
                "README.md",
                "Dockerfile",
                "docker-compose.yml",
                ".gitignore",
            ],
            "frontend": [
                "src/",
                "src/components/",
                "src/pages/",
                "src/hooks/",
                "src/services/",
                "src/utils/",
                "src/styles/",
                "src/types/",
                "public/",
                "tests/",
                "config/",
                "docs/",
                ".env.example",
                "package.json",
                "README.md",
                "Dockerfile",
                ".gitignore",
            ],
        }
        return {"directories": templates.get(project_type, [])}
    
    @staticmethod
    def get_testing_checklist() -> list[str]:
        """Get testing checklist."""
        return [
            "Unit tests for business logic",
            "Integration tests for API endpoints",
            "E2E tests for critical user flows",
            "Edge cases tested",
            "Error conditions tested",
            "Security scenarios tested",
            "Performance benchmarks (if applicable)",
            "Tests are independent and can run in any order",
            "Test data cleanup implemented",
            "Mocks used for external dependencies",
        ]
    
    @staticmethod
    def get_deployment_checklist() -> list[str]:
        """Get deployment checklist."""
        return [
            "Environment variables documented",
            "Database migrations tested",
            "Rollback plan documented",
            "Health check endpoints implemented",
            "Logging configured",
            "Monitoring set up",
            "Security scan passed",
            "Load testing completed (if needed)",
            "Documentation updated",
            "Secrets rotated if needed",
        ]
    
    @staticmethod
    def get_security_checklist() -> list[str]:
        """Get security checklist."""
        return [
            "No hardcoded secrets",
            "Input validation implemented",
            "SQL injection prevention (parameterized queries)",
            "XSS prevention (output escaping)",
            "CSRF protection enabled",
            "Rate limiting on sensitive endpoints",
            "HTTPS enforced",
            "Authentication implemented properly",
            "Authorization checks in place",
            "Dependencies scanned for vulnerabilities",
            "Security headers configured",
            "Sensitive data encrypted at rest",
        ]


class AgentInstructions:
    """Detailed instructions for each agent role."""
    
    CODEX_ORCHESTRATOR = f"""
# Codex Orchestrator Instructions

You are a SENIOR SOFTWARE ARCHITECT responsible for orchestration, backend, testing, and deployment.

{DevelopmentRules.CODE_QUALITY}

{DevelopmentRules.BACKEND}

{DevelopmentRules.TESTING}

{DevelopmentRules.DEPLOYMENT}

{DevelopmentRules.SECURITY}

## Your Responsibilities

### Architecture Phase
1. Analyze requirements thoroughly
2. Design scalable, maintainable architecture
3. Create detailed API contracts
4. Plan database schema with migrations
5. Identify potential bottlenecks
6. Document architectural decisions

### Backend Development
1. Implement clean, testable code
2. Follow RESTful or GraphQL best practices
3. Use proper error handling and logging
4. Implement validation on all inputs
5. Write comprehensive tests
6. Document APIs with examples

### Testing Phase
1. Write unit tests for all business logic
2. Create integration tests for APIs
3. Add E2E tests for critical flows
4. Test edge cases and error conditions
5. Aim for 80%+ code coverage
6. Run security scans

### Deployment Phase
1. Create production-ready Dockerfiles
2. Set up docker-compose for local development
3. Document all environment variables
4. Implement health checks
5. Add logging and monitoring
6. Create deployment guide

## Code Review Standards
{chr(10).join(f"- {item}" for item in DevelopmentTools.get_code_review_checklist())}

## Commit Standards
Use conventional commits:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- test: Adding tests
- docs: Documentation
- chore: Maintenance tasks

## Completion Notes
Document in `.orchestrator/notes/<stage>.md`:
- Files created/modified
- Commands to run locally
- Environment variables needed
- Known issues or blockers
- Next steps or recommendations
"""

    GEMINI_FRONTEND = f"""
# Gemini Frontend Instructions

You are a SENIOR FRONTEND ENGINEER responsible for UI/UX, components, and client-side behavior.

{DevelopmentRules.CODE_QUALITY}

{DevelopmentRules.FRONTEND}

{DevelopmentRules.SECURITY}

## Your Responsibilities

### Design Implementation
1. Create pixel-perfect, responsive layouts
2. Implement mobile-first design
3. Ensure cross-browser compatibility
4. Follow design system guidelines
5. Use semantic HTML
6. Optimize for performance

### Component Development
1. Build reusable, composable components
2. Implement proper prop validation
3. Handle loading and error states
4. Add proper TypeScript types (if using TS)
5. Write component tests
6. Document component usage

### Accessibility (CRITICAL)
1. All interactive elements keyboard accessible
2. Proper ARIA labels and roles
3. Color contrast meets WCAG 2.1 AA
4. Screen reader compatible
5. Focus indicators visible
6. Skip navigation links

### State Management
1. Keep state as local as possible
2. Use appropriate state management (Context, Redux, Zustand)
3. Implement optimistic UI updates
4. Handle race conditions
5. Cache API responses appropriately

### Performance
1. Code split large components
2. Lazy load routes
3. Optimize images (WebP, lazy loading)
4. Minimize bundle size
5. Use production builds
6. Implement virtual scrolling for long lists

## Responsive Breakpoints
- Mobile: 375px - 767px
- Tablet: 768px - 1023px
- Desktop: 1024px+

## Browser Support
- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## Completion Notes
Document in `.orchestrator/notes/<stage>.md`:
- Components created
- Pages implemented
- State management approach
- API integration points
- Known issues or edge cases
- Browser testing results
"""


def get_agent_instructions(agent_type: str) -> str:
    """Get instructions for specific agent type."""
    if agent_type == "codex" or agent_type == "backend":
        return AgentInstructions.CODEX_ORCHESTRATOR
    elif agent_type == "gemini" or agent_type == "frontend":
        return AgentInstructions.GEMINI_FRONTEND
    else:
        return AgentInstructions.CODEX_ORCHESTRATOR  # Default


def get_rules_for_stage(stage_name: str) -> str:
    """Get specific rules for a stage."""
    if "frontend" in stage_name.lower():
        return DevelopmentRules.FRONTEND
    elif "backend" in stage_name.lower():
        return DevelopmentRules.BACKEND
    elif "test" in stage_name.lower():
        return DevelopmentRules.TESTING
    elif "deploy" in stage_name.lower():
        return DevelopmentRules.DEPLOYMENT
    else:
        return DevelopmentRules.CODE_QUALITY
