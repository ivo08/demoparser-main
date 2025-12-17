// dashboard.js

document.addEventListener("DOMContentLoaded", () => {
    
    // --- Funções de Custo (Inalteradas) ---

    // Recalcular custo sempre que algo for selecionado
    function recalcTeam(team) {
        let total = 0;
        
        // Para cada jogador
        document.querySelectorAll(`input[name^=\"${team}_player_\"]`).forEach((input, i) => {
            const primary = document.querySelector(`input[name=\"${team}_primary_${i}\"]`)?.value || "";
            const secondary = document.querySelector(`input[name=\"${team}_secondary_${i}\"]`)?.value || "";
            const grenades = document.querySelector(`input[name=\"${team}_grenades_${i}\"]`)?.value || "";
            const equipment = document.querySelector(`input[name=\"${team}_equipment_${i}\"]`)?.value || "";

            if (primary && WEAPON_MAP['primary_weapons'][primary]) total += WEAPON_MAP['primary_weapons'][primary];
            if (secondary && WEAPON_MAP['secondary_weapons'][secondary]) total += WEAPON_MAP['secondary_weapons'][secondary];

            if (grenades) {
                grenades.split(",").forEach(g => {
                    if (g && WEAPON_MAP['grenades'][g]) total += WEAPON_MAP['grenades'][g];
                });
            }
            if (equipment) {
                equipment.split(",").forEach(e => {
                    if (e && WEAPON_MAP['equipment'][e]) total += WEAPON_MAP['equipment'][e];
                });
            }
        });

        const equipSpan = document.getElementById(`${team}-equip`);
        if (equipSpan) equipSpan.textContent = total.toLocaleString();
    }


    // --- NOVO: Lógica de Seleção de Equipa ---

    function setPlayers(teamSide, teamKey) {
        console.log(TEAM_PRESETS);
        
        // Verifica se TEAM_PRESETS existe e se a chave da equipa é válida
        const presets = TEAM_PRESETS && TEAM_PRESETS[teamKey];
        
        // Seleciona todos os inputs de jogador para o lado da equipa (ex: ct_player_0, ct_player_1, ...)
        const playerInputs = document.querySelectorAll(`input[name^="${teamSide}_player_"]`);

        // JSON values to array
        const players_steamids = Object.values(presets);
        const players_names = Object.keys(presets);
        console.log(players_steamids);

        if (!players_steamids || players_steamids.length !== 5) {
            console.log("Limpando. Presets:", presets, "| Presets.length:", presets.length);
            // Limpar campos se a seleção for nula ou o preset for inválido
            playerInputs.forEach(input => {
                input.value = "";
            });
            return;
        }

        // Preenche os campos de input do jogador (steamid)
        playerInputs.forEach((input, i) => {
            console.log(input);
            if (i < players_steamids.length) {
                input.value = players_names[i];
                input.dataset.steamid = players_steamids[i];
            } else {
                input.value = "";
                input.dataset.steamid = "";
            }
        });
        
        // Não limpamos o equipamento automaticamente, mas seria uma boa prática.
    }

    function handleSubmit(event) {
        event.preventDefault();

        // Get team players for both teams
        var ct_team_players = document.querySelectorAll('input[name^="ct_player_"]');
        var t_team_players = document.querySelectorAll('input[name^="t_player_"]');
        
        // Prepare data object
        var data = {
            team_ct_current_equip_value: document.getElementById('ct-equip').textContent,
            team_t_current_equip_value: document.getElementById('t-equip').textContent,
            ct_team_players: [],
            t_team_players: []
        }

        // Iterate over the ct_team_players array and extract the steamid attribute
        ct_team_players_steamid = [];
        ct_team_players.forEach(element => {
            // Get the data-steamid attribute from the input element
            const steamid = element.dataset.steamid;
            ct_team_players_steamid.push(steamid);
        });
        data["ct_team_players"] = ct_team_players_steamid;

        // Iterate over the t_team_players array and extract the steamid attribute
        t_team_players_steamid = [];
        t_team_players.forEach(element => {
            // Get the data-steamid attribute from the input element
            const steamid = element.dataset.steamid;
            t_team_players_steamid.push(steamid);
        });
        data["t_team_players"] = t_team_players_steamid;

        // Send POST request to the API endpoint
        fetch('http://127.0.0.1:8000/api/predict/', {
            method: 'POST',
            body: JSON.stringify(data),
            headers: {
                'Content-Type': 'application/json'
            }
        })
    }

const form = document.querySelector('form');
form.addEventListener('submit', handleSubmit);

    // ------------------------------------------------------------
    // Event Listeners
    // ------------------------------------------------------------
    
    // 1. Seleção de Equipa (NOVO)
    const ctSelect = document.getElementById('ct-team-select');
    const tSelect = document.getElementById('t-team-select');
    
    if (ctSelect) {
        ctSelect.addEventListener('change', (e) => {
            const teamKey = e.target.value;
            setPlayers('ct', teamKey);
        });
    }

    if (tSelect) {
        tSelect.addEventListener('change', (e) => {
            const teamKey = e.target.value;
            setPlayers('t', teamKey);
        });
    }


    // 2. Seleção de Ícones (Inalterado)
    document.querySelectorAll('.weapon-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            const { team, type, slot, name } = icon.dataset;
            const playerCard = icon.closest('.player-card');

            // Lógica de seleção (primária/secundária vs granada/equipamento)
            if (type === 'primary' || type === 'secondary') {
                // Deselecionar todos os outros ícones do mesmo tipo e slot
                playerCard.querySelectorAll(`.weapon-icon[data-type="${type}"]:not([data-name="${name}"])`)
                    .forEach(i => i.classList.remove('selected'));
                
                // Toggle para o ícone clicado
                icon.classList.toggle('selected');

                // Atualizar hidden input
                const isSelected = icon.classList.contains('selected');
                const value = isSelected ? name : "";

                const input = playerCard.querySelector(`input[name=\"${team}_${type}_${slot}\"]`);
                if (input) input.value = value;
                
            } else if (type === 'grenade') {
                // Multi-seleção para granadas
                icon.classList.toggle('selected');

                const selected = [...playerCard.querySelectorAll('.weapon-icon.grenade.selected')]
                    .map(i => i.dataset.name);

                const input = playerCard.querySelector(`input[name=\"${team}_grenades_${slot}\"]`);
                if (input) input.value = selected.join(',');
            } else if (type === 'equipment') {
                // Multi-seleção para equipamento
                icon.classList.toggle('selected');

                const selected = [...playerCard.querySelectorAll('.weapon-icon.equipment.selected')]
                    .map(i => i.dataset.name);

                const input = playerCard.querySelector(`input[name=\"${team}_equipment_${slot}\"]`);
                if (input) input.value = selected.join(',');
            }

            // Recalcular custo da equipa
            recalcTeam(team);
        });
    });

    // ------------------------------------------------------------
    //  DEFAULT: Selecionar automaticamente USP-S/P2000/Glock-18
    // ------------------------------------------------------------
    const DEFAULT_PISTOL = "USP-S/P2000/Glock-18";

    document.querySelectorAll('.weapon-icon[data-type=\"secondary\"]').forEach(icon => {
        if (icon.dataset.name === DEFAULT_PISTOL) {
            const { team, slot } = icon.dataset;

            // Marcar como selecionada
            icon.classList.add("selected");

            // Atualizar hidden input
            const hidden = icon.closest('.player-card')
                .querySelector(`input[name=\"${team}_secondary_${slot}\"]`);

            if (hidden) hidden.value = DEFAULT_PISTOL;
        }
    });

    document.querySelector('#predict-form').addEventListener('submit', handleSubmit);

    // Recalcular já no início (todas as pistolas default)
    recalcTeam("ct");
    recalcTeam("t");
});