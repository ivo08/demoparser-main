document.addEventListener("DOMContentLoaded", () => {

    // Recalcular custo sempre que algo for selecionado
    function recalcTeam(team) {
        let total = 0;
        console.log(`Recalculating ${team} team equip`);

        // Para cada jogador
        document.querySelectorAll(`input[name^="${team}_player_"]`).forEach((input, i) => {
            const primary = document.querySelector(`input[name="${team}_primary_${i}"]`)?.value || "";
            const secondary = document.querySelector(`input[name="${team}_secondary_${i}"]`)?.value || "";
            const grenades = document.querySelector(`input[name="${team}_grenades_${i}"]`)?.value || "";
            const equipment = document.querySelector(`input[name="${team}_equipment_${i}"]`)?.value || "";

            console.log(`Recalculating ${team} team equip for player ${i}: ${primary}, ${secondary}, ${grenades}, ${equipment}`);

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
            console.log(`Equipement selected was ${equipment} and total is now ${total}`);
        });

        // Atualiza o preview no HTML
        const target = document.getElementById(`${team}-equip`);
        if (target) target.textContent = total;
    }

    // Clicar num ícone de arma
    document.querySelectorAll('.weapon-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            const { team, type, name, slot } = icon.dataset;
            const playerCard = icon.closest('.player-card');

            console.log(`Clicked ${type} on ${team} slot ${slot} for ${name}`);

            if (type === 'primary' || type === 'secondary') {

                // Desmarcar as outras do mesmo tipo
                playerCard.querySelectorAll(`.weapon-icon[data-type="${type}"]`)
                    .forEach(i => i.classList.remove('selected'));

                icon.classList.add('selected');

                // Atualizar hidden input
                const input = playerCard.querySelector(`input[name="${team}_${type}_${slot}"]`);
                if (input) input.value = name;

            } else if (type === 'grenade') {
                icon.classList.toggle('selected');

                const selected = [...playerCard.querySelectorAll('.weapon-icon.grenade.selected')]
                    .map(i => i.dataset.name);

                const input = playerCard.querySelector(`input[name="${team}_grenades_${slot}"]`);
                if (input) input.value = selected.join(',');
            } else if (type === 'equipment') {

                icon.classList.toggle('selected');

                const selected = [...playerCard.querySelectorAll('.weapon-icon.equipment.selected')]
                    .map(i => i.dataset.name);

                const input = playerCard.querySelector(`input[name="${team}_equipment_${slot}"]`);
                if (input) input.value = selected.join(',');
            }

            // Recalcular custo da equipa
            recalcTeam(team);
        });
    });

    // -------------------------------------------------------------
    //  DEFAULT: Selecionar automaticamente USP-S/P2000/Glock-18
    // -------------------------------------------------------------
    const DEFAULT_PISTOL = "USP-S/P2000/Glock-18";

    document.querySelectorAll('.weapon-icon[data-type="secondary"]').forEach(icon => {
        if (icon.dataset.name === DEFAULT_PISTOL) {
            const { team, slot } = icon.dataset;

            // Marcar como selecionada
            icon.classList.add("selected");

            // Atualizar hidden input
            const hidden = icon.closest('.player-card')
                .querySelector(`input[name="${team}_secondary_${slot}"]`);

            if (hidden) hidden.value = DEFAULT_PISTOL;
        }
    });

    // Recalcular já no início (todas as pistolas default)
    recalcTeam("ct");
    recalcTeam("t");
});
