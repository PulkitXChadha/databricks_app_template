# Constitutional Deviation: 003-obo-only-support

**Feature**: Remove Service Principal Fallback - OBO-Only Authentication  
**Date**: 2025-10-15  
**Constitution Version**: v1.2.0  
**Status**: Approved and Implemented

## Deviation Summary

This feature intentionally deviates from Constitution v1.2.0 Principle "Dual Authentication Patterns" by removing service principal fallback authentication for Databricks API operations. The application now uses **OBO-only authentication** for all Databricks API services.

## Affected Constitutional Principle

**Original Principle**: "Dual Authentication Patterns"
- Pattern A: Service Principal (Application-Level Authorization) for app-level operations
- Pattern B: On-Behalf-Of User (OBO) for user-level operations
- Automatic fallback from Pattern B to Pattern A when user context unavailable

**Deviation**: Removed Pattern A fallback for Databricks APIs
- **Databricks API operations**: OBO-only (Pattern B exclusively)
- **Lakebase operations**: Maintains Pattern A (application-level credentials with user_id filtering)
- **No automatic fallback** for any Databricks API service

## Justification

### User Requirements
1. **Explicit request**: User stated "no need for backward compatibility"
2. **Security priority**: User prioritized security over convenience
3. **Simplified architecture**: User preferred single authentication path

### Technical Benefits
1. **Strengthened security posture**: Eliminates privilege escalation risk
2. **Simplified codebase**: Removed ~300 lines of fallback logic
3. **Clearer audit trails**: All operations tied to actual users
4. **Reduced complexity**: Single authentication path easier to maintain
5. **Better permission enforcement**: Unity Catalog permissions always respected

### Architectural Improvements
1. **No unauthorized access**: App cannot bypass user permissions
2. **Consistent behavior**: All API calls use same authentication method
3. **Predictable errors**: Clear 401 responses when authentication fails
4. **Zero-trust model**: Every request requires valid user context

## Scope of Deviation

### What Changed
- **UnityCatalogService**: Removed service principal fallback, requires user_token
- **ModelServingService**: Removed service principal fallback, requires user_token
- **UserService**: Removed service principal fallback, requires user_token
- **AuthenticationContext**: Removed auth_mode field (always OBO)
- **Metrics**: Removed auth_fallback_total counter
- **Logging**: Removed auth.fallback_triggered events
- **/metrics endpoint**: Now requires authentication (was public)

### What Remained Unchanged
- **LakebaseService**: Maintains Pattern A (application-level credentials)
  - Rationale: Database connection pooling incompatible with per-user credentials
  - Security: User isolation enforced via user_id filtering in queries
- **/health endpoint**: Remains public (no authentication required)
- **Error handling**: Maintains structured error responses with correlation IDs
- **Observability**: Maintains structured logging and metrics

## Migration Impact

### Breaking Changes
- **Local development**: Requires Databricks CLI authentication (`databricks auth token`)
- **API requests**: Must include `X-Forwarded-Access-Token` header
- **Service initialization**: All Databricks API services raise ValueError without user_token
- **Metrics endpoint**: Now requires authentication (previously public)

### Migration Path
1. Local development: Use `databricks auth token` to obtain user tokens
2. Testing: Update test fixtures to provide user tokens
3. Deployed apps: No changes needed (Databricks Apps provide tokens automatically)

## Constitutional Alignment

### Maintained Principles
- ✅ **Design Bricks First**: No UI changes (backend-only refactoring)
- ✅ **Lakebase Integration**: Hybrid approach preserved (Pattern A with user_id filtering)
- ✅ **Asset Bundle Deployment**: No deployment changes
- ✅ **Type Safety Throughout**: All type hints maintained
- ✅ **Model Serving Integration**: OBO-only enforced
- ✅ **Auto-Generated API Clients**: Regenerated after changes
- ✅ **Development Tooling Standards**: uv and bun unchanged
- ✅ **Observability First**: Structured logging and metrics maintained
- ✅ **Multi-User Data Isolation**: Strengthened by OBO-only enforcement

### Deviated Principle
- ⚠️ **Dual Authentication Patterns**: Removed for Databricks APIs
  - **Justification**: User requirement for simplified, secure architecture
  - **Mitigation**: LakebaseService maintains hybrid approach where appropriate
  - **Impact**: Positive - strengthened security, simplified codebase

## Documentation Updates

All documentation updated to reflect OBO-only architecture:
- ✅ `docs/OBO_AUTHENTICATION.md`: Removed service principal references
- ✅ `docs/LOCAL_DEVELOPMENT.md`: Updated with CLI token workflow
- ✅ `docs/DEPLOYMENT_CHECKLIST.md`: Removed service principal requirements
- ✅ `README.md`: Updated environment variables section
- ✅ `CLAUDE.md`: Added OBO-only authentication architecture section
- ✅ `specs/003-obo-only-support/`: Complete implementation documentation

## Implementation Summary

**Tasks Completed**: 46 tasks (T001-T044)
- Phase 2: Test infrastructure (T001-T003) ✓
- Phase 3: OBO-only enforcement (T004-T017b) ✓
- Phase 4: Local development (T018-T020) ✓
- Phase 5: Clear error messages (T021-T025) ✓
- Phase 6: Documentation updates (T026-T029) ✓
- Phase 7: Configuration cleanup (T030-T032) ✓
- Phase 8: Health/metrics endpoints (T033-T036) ✓
- Phase 9: Polish & validation (T037-T044) ✓

**Code Changes**:
- Modified: 16 files
- Lines removed: ~300 (fallback logic)
- Lines added: ~200 (tests, error handling, documentation)
- Net simplification: ~100 lines removed

**Testing**:
- Contract tests: Verify OBO-only enforcement
- Integration tests: Validate multi-user scenarios
- Error handling tests: Structured 401 responses

## Approval

**Approved by**: User (via explicit requirement "no need for backward compatibility")  
**Date**: 2025-10-15  
**Rationale**: Security improvement outweighs backward compatibility concerns

## Future Considerations

1. **Background Jobs**: If added, will need separate authentication strategy
2. **Service Accounts**: If required, implement via dedicated OBO tokens
3. **Admin Operations**: Must use admin user tokens, not service principal
4. **Monitoring**: Metrics endpoint authentication may be revisited for monitoring systems

## Conclusion

This deviation from the "Dual Authentication Patterns" principle is justified by:
1. Explicit user requirement for simplified architecture
2. Significant security improvement (no privilege escalation)
3. Reduced code complexity and maintenance burden
4. Maintained constitutional compliance for database operations (LakebaseService hybrid approach)

The deviation strengthens the application's security posture while maintaining all other constitutional principles. The hybrid approach for LakebaseService demonstrates that the constitution allows for appropriate pattern selection based on technical constraints.

---

**Related Documents**:
- Feature Spec: `specs/003-obo-only-support/spec.md`
- Implementation Plan: `specs/003-obo-only-support/plan.md`
- Task List: `specs/003-obo-only-support/tasks.md`
- OBO Authentication Guide: `docs/OBO_AUTHENTICATION.md`

