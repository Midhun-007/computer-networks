set(tcp_dqn_sources
    model/tcp-dqn-env.cc
    model/tcp-dqn-congestion-ops.cc
    helper/tcp-dqn-helper.cc
)

set(tcp_dqn_headers
    model/tcp-dqn-env.h
    model/tcp-dqn-congestion-ops.h
    model/tcp-dqn-constants.h
    helper/tcp-dqn-helper.h
    helper/tcp-dqn-topology-helper.h
)

build_lib(
    LIBNAME tcp-dqn
    SOURCE_FILES ${tcp_dqn_sources}
    HEADER_FILES ${tcp_dqn_headers}
    LIBRARIES_TO_LINK
        ${libai}
        ${libinternet}
        ${libnetwork}
        ${libcore}
    TEST_SOURCES test/tcp-dqn-test-suite.cc
)
