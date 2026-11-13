/**
 * Référence « Ask me anything » : accueil conversationnel épuré.
 * L'onde n'est animée que pendant une demande réelle (`active`), sinon elle reste
 * statique et atténuée : aucune animation décorative permanente.
 */
export function AskHero({ active, modelReady }: { active: boolean; modelReady: boolean }) {
  const traces = [0, 1, 2, 3, 4, 5];
  return (
    <div className="ask-hero">
      <div className={active ? 'ask-frame ask-frame--active' : 'ask-frame'}>
        <h1 id="workbench-title" className="ask-title">
          {active ? 'HORIZON traite votre demande…' : 'Demandez ce que vous voulez…'}
        </h1>
        <svg
          className={active ? 'ask-wave ask-wave--active' : 'ask-wave'}
          viewBox="0 0 620 130"
          role="img"
          aria-label={active ? 'Demande en cours de traitement' : 'Aucune demande en cours'}
        >
          {traces.map((index) => {
            const spread = 1 - index * 0.13;
            return (
              <path
                key={index}
                d={`M8 65 C 120 ${65 - 46 * spread}, 150 ${65 + 46 * spread}, 250 ${65 - 34 * spread}
                    C 330 ${65 + 40 * spread}, 360 ${65 - 30 * spread}, 440 ${65 + 22 * spread}
                    C 510 ${65 - 18 * spread}, 560 ${65 + 10 * spread}, 612 65`}
                fill="none"
                stroke="currentColor"
                strokeWidth={0.9}
                strokeLinecap="round"
                opacity={0.16 + index * 0.13}
                style={{ animationDelay: `${index * 90}ms` }}
              />
            );
          })}
        </svg>
        <p className="ask-hint">
          {active
            ? 'Requête en cours auprès du moteur local.'
            : modelReady
              ? 'Un fournisseur est configuré : la réponse sera produite par le modèle local.'
              : 'Aucun fournisseur IA configuré : le message est enregistré avec le statut accepted_no_model.'}
        </p>
      </div>
    </div>
  );
}

export default AskHero;