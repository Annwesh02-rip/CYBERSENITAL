from sklearn.decomposition import PCA


def fit_pca(scaled_features, n_components: int = 2):
    pca = PCA(n_components=n_components, random_state=42)
    projected = pca.fit_transform(scaled_features)
    return pca, projected
