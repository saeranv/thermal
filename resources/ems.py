def swap_spc_light(act_osm, ref_osm):
    """Swap space lighting."""

    ## Get resources
    light_sched_name = "OfficeMedium BLDG_LIGHT_SCH_2013"
    #ref_sched_opt = ref_osm.getScheduleByName(light_sched_name)
    #ref_sched = assert_init(ref_sched_opt).get()
    #act_sched = swap_modelobj(ref_sched, act_osm)

    # Get all spaces, and sort them
    ref_spcs, act_spcs = ref_osm.getSpaces(), act_osm.getSpaces()
    ref_spcs, act_spcs = match_spc(ref_spcs, act_spcs)

    ## Loop through spaces and remove/then assign light_defn to space
    for ref_spc, act_spc in zip(ref_spcs, act_spcs):
        ref_name, act_name = ref_spc.nameString(), act_spc.displayName()
        ref_spc_type = assert_init(ref_spc.spaceType()).get()
        act_spc_type = assert_init(act_spc.spaceType()).get()

        # DaylightSensors
        ref_controls = ref_spc.daylightingControls()
        if len(ref_controls) == len(act_spc.daylightingControls()):
            continue

        # Space lights
        for act_spc_light in act_spc.lights():
            act_spc_light.remove()
        for ref_type_light in ref_spc_type.lights():
            # Get sched
            ref_light = assert_init(ref_type_light.to_Lights()).get()
            act_light_opt = swap_modelobj(ref_light, act_osm)
            act_light = assert_init(act_light_opt.to_Lights()).get()
            is_parent_set = act_light.setParent(act_spc)
            assert is_parent_set, "setParent fail for {}".format(act_light)
            # Swap schedule
            act_sched_opt = act_osm.getScheduleByName(light_sched_name)
            act_sched = assert_init(act_sched_opt).get()
            is_sched = act_light.setSchedule(act_sched)
            print('Added {} to space: {}'.format(act_light.nameString(), act_name))

        for ref_control in ref_controls:
            act_control = swap_modelobj(ref_control, act_osm)
            is_parent_set = act_control.setParent(act_spc)
            assert is_parent_set, "setParent fail for {}".format(act_control)
            print('Added {} to space: {}'.format(
                  act_control.nameString(), act_name))
    ems_data = {
        'sensor_name': [],
        'actuated_comp': []
    }

    for ems_sensor in ref_osm.getEnergyManagementSystemSensors():
        ems_sensor_var = ems_sensor.outputVariableOrMeterName()
        if "Lights" not in ems_sensor_var:
            continue
        act_ems_sensor = swap_modelobj(ems_sensor, act_osm)
        ems_data['sensor_name'] += [act_ems_sensor.nameString()]
    for ems_actuator in ref_osm.getEnergyManagementSystemActuators():
        if "Lights" not in ems_actuator.actuatedComponentType():
            continue
        act_ems_actuator = swap_modelobj(ems_actuator, act_osm)
        act_ems_actuator = act_ems_actuator.to_EnergyManagementSystemActuator()
        act_ems_actuator = assert_init(act_ems_actuator).get()
        #comp = assert_init(act_ems_actuator.actuatedComponent()).get()
        #ems_data['actuated_comp'] += [comp.nameString()]
    for ems_glob_var in ref_osm.getEnergyManagementSystemGlobalVariables():
        swap_modelobj(ems_glob_var, act_osm)
    #for ems_out_var in ref_osm.getEnergyManagementSystemOutputVariables():
    #    swap_modelobj(ems_out_var, act_osm)
    for ems_int_var in ref_osm.getEnergyManagementSystemInternalVariables():
        swap_modelobj(ems_int_var, act_osm)
    # Programs
    for ems_prog_call in ref_osm.getEnergyManagementSystemProgramCallingManagers():
        ems_prog_call_name = ems_prog_call.nameString()
        if "Light" not in ems_prog_call_name:
            continue
        act_prog_call = swap_modelobj(ems_prog_call, act_osm)
        act_prog_call = act_prog_call.to_EnergyManagementSystemProgramCallingManager()
        act_prog_call = assert_init(act_prog_call).get()
        # Swap program
        ems_prog = assert_init(ems_prog_call.getProgram(0)).get()
        act_prog = swap_modelobj(ems_prog, act_osm)
        act_prog = assert_init(act_prog.to_EnergyManagementSystemProgram()).get()
        act_prog_call.eraseProgram(0)
        act_prog_call.addProgram(act_prog)

    #for ems_prog in ref_osm.getEnergyManagementSystemPrograms():
    #    swap_modelobj(ems_prog, act_osm)
    #ems_progs = act_osm.getEnergyManagementSystemPrograms()
    #ems_prog_calls = act_osm.getEnergyManagementSystemProgramCallingManagers()
    #for ems_prog, ems_prog_call in zip(ems_progs, ems_prog_calls):
    #    ems_prog_call.eraseProgram(0)
    #    ems_prog_call.addProgram(ems_prog)

    return act_osm

