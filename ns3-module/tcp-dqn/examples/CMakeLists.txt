build_lib_example(
    NAME tcp-dqn-topology
    SOURCE_FILES tcp-dqn-topology.cc
    LIBRARIES_TO_LINK
        ${libtcp-dqn}
        ${libai}
        ${libcore}
        ${libpoint-to-point}
        ${libnetwork}
        ${libapplications}
        ${libinternet}
)

build_lib_example(
    NAME tcp-dqn-baselines-topology
    SOURCE_FILES tcp-dqn-baselines-topology.cc
    LIBRARIES_TO_LINK
        ${libtcp-dqn}
        ${libcore}
        ${libpoint-to-point}
        ${libnetwork}
        ${libapplications}
        ${libinternet}
)
