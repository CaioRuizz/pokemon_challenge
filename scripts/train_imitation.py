#!/usr/bin/env python3
"""Treina o modelo linear de imitation learning a partir do dataset gerado
por scripts/build_imitation_dataset.py, e imprime os pesos para colar em
agent/policy_ml.py (_WEIGHTS). Requer numpy + scikit-learn (só nesta etapa
de treino offline — o agente final não depende de nenhum dos dois).

Uso:
    python scripts/train_imitation.py --dataset data/ml/dataset.npz
"""
import argparse

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    data = np.load(args.dataset)
    X, y = data["X"], data["y"]
    print(f"{X.shape[0]} pares de treino, {X.shape[1]} features, {int(data['n_decisions'])} decisões originais")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=0)
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(X_train, y_train)
    print(f"acurácia treino: {clf.score(X_train, y_train):.4f}")
    print(f"acurácia teste:  {clf.score(X_test, y_test):.4f}")

    w = clf.coef_[0]
    print("\n_WEIGHTS = [")
    for i in range(0, len(w), 8):
        print("    " + ", ".join(f"{v:.6f}" for v in w[i : i + 8]) + ",")
    print("]")
    print(f"# intercept (não usado — irrelevante para ranking relativo): {clf.intercept_[0]:.6f}")


if __name__ == "__main__":
    main()
