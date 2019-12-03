import numpy as np
from scipy import linalg

class GaussianProcess:
    def compute_rho_corr_func_point(self, a, b, this_rho):
        """Compute correlation between two points a and b."""
        corr = np.prod(this_rho**(4 * (a - b)**2))
        return corr


    def compute_rho_corr_func(self, a, b, this_rho):
        """Compute rho correlation function between two vectors a and b.
        Returns kernel matrix [len(a), len(b)]."""
        corr_matrix = [self.compute_rho_corr_func_point(a[i], b[j], this_rho)
            for i in range(a.shape[0]) for j in range(b.shape[0])]
        return np.array(corr_matrix).reshape(a.shape[0], -1)


    def __init__(self, x, y, prec_f, cov_n, rho=None):
        """Compute design covariance matrix and ln-likelihood.
        Parameters
        ----------
            x: design points [N_data, N_dim_input]
            y: design values [N_data, N_output]
            rho: rho parameter [N_output, N_dim_input]
            prec_f: precision of the GP
            cov_n: covariance of y [N_output*N_data, N_output*N_data]
        Returns
        -------
            None
        """

        # Check dimensions
        # if len(y)!=len(x):
        #     raise TypeError("Number of design points %d must match number of design values %d"%(len(y), len(x)))
        self.N_data = len(x)
        self.N_dim_input = x.shape[1]
        self.N_output = y.shape[1]
        # assert len(prec_f)==self.N_output, \
        #     "Number of GP vars %d does not match number of outputs %d"%(len(prec_f), self.N_output)
        # assert cov_n.shape==(self.N_output*self.N_data, self.N_output*self.N_data), \
        #     "Your measurement errors have the wrong shape (%s,%s) for %d GPs in %s dimensions."%(
        #     cov_n.shape[0], cov_n.shape[1], self.N_output, self.N_data)
        # assert rho.shape==(self.N_output, self.N_dim_input), \
        #     "Your correlation lengths have shape (%d,%d), but data has (%d,%d)"%(
        #         rho.shape[0], rho.shape[1], self.N_output, self.N_dim_input)
        # assert len(prec_f)==self.N_output, \
        #     "prec_f has wrong shape %d, but %d GPs"%(len(prec_f), self.N_output)

        self.x = x
        self.corr_rho = rho
        self.prec_f = prec_f
        self.y_flat = y.flatten(order='F')

        # Correlation matrix
        self.corrmat = np.zeros((self.N_output*self.N_data, self.N_output*self.N_data))
        for i in range(self.N_output):
            self.corrmat[i*self.N_data:(i+1)*self.N_data, i*self.N_data:(i+1)*self.N_data] = self.compute_rho_corr_func(x, x, self.corr_rho[i])/self.prec_f[i]
        try:
            self.cholesky_factor = linalg.cho_factor(self.corrmat + cov_n)
        except:
            print("Could not compute Cholesky decomposition")
            self.lnlike = -np.inf
            return
        self.Krig_basis = linalg.cho_solve(self.cholesky_factor, self.y_flat)


    def predict(self, x_new):
        """
        Parameters: evaluation points [N_dim_input]
        Returns: (mean, variance)
        """

        if len(x_new)!=self.N_dim_input:
            raise TypeError("Evaluation points %s needs to be shape %d"%(len(x_new), self.N_dim_input))

        # Correlation with design input [N_output, N_data]
        corr_xnew_x = np.zeros((self.N_output, self.N_output*self.N_data))
        for i in range(self.N_output):
            corr_xnew_x[i,i*self.N_data:(i+1)*self.N_data] = [self.compute_rho_corr_func_point(x_new, self.x[j], self.corr_rho[i])
                                                              for j in range(self.N_data)]
        corr_xnew_x/= self.prec_f[:,None]

        # Mean prediction
        eval_mean = np.dot(corr_xnew_x, self.Krig_basis)

        # Variance
        v = linalg.cho_solve(self.cholesky_factor, corr_xnew_x.T)
        eval_covmat = np.diag(1./self.prec_f) - np.dot(corr_xnew_x, v)

        return eval_mean, eval_covmat
