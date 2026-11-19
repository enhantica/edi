set pagination off
set confirm off
set breakpoint pending on
set print thread-events off
set $measuring = 0
set $calculations = 0
set $parses = 0
set $renders = 0
break edi_link_probe_phase
commands
silent
if $measuring
printf "ENGINE_COUNTS calls=%d parses=%d renders=%d\n", $calculations, $parses, $renders
set $measuring = 0
else
set $calculations = 0
set $parses = 0
set $renders = 0
set $measuring = 1
end
continue
end
break 'crysta::calculate_project(crysta::Project&, crysta::DueEstimates)'
commands
silent
if $measuring
set $calculations = $calculations + 1
end
continue
end
break crysta::parse_edi
commands
silent
if $measuring
set $parses = $parses + 1
end
continue
end
break 'crysta::EdiLoop::render_lines[abi:cxx11]() const'
commands
silent
if $measuring
set $renders = $renders + 1
end
continue
end
run
