import matplotlib.pyplot as plt
import seaborn as sns

def plot_bar_chart(data,x_column,y_column,title=None,x_label=None,y_label=None,color='red',save_path=None):
    plt.figure(figsize=(10,6))
    sns.barplot(x=x_column,y=y_column,data=data,color=color)
    if title:
        plt.title = title
    if x_label:
        plt.x_label = x_label
    if y_label:
        plt.y_label = y_label
    if save_path:
        plt.savefig(save_path)
    
    plt.show()

def plot_line_chart(data,x_column,y_column,title=None,x_label=None,y_label=None,color='red',save_path=None):
    plt.figure(figsize=(10,6))
    sns.barplot(data[x_column],data[y_column],color=color)
    if title:
        plt.title = title
    if x_label:
        plt.x_label = x_label
    if y_label:
        plt.y_label = y_label
    if save_path:
        plt.savefig(save_path)
    
    plt.show()

def plot_histogram(data, column, title=None, xlabel=None, ylabel=None, bins=10, color='blue', save_path=None):
    plt.figure(figsize=(10, 6))
    plt.hist(data[column], bins=bins, color=color)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if save_path:
        plt.savefig(save_path)
    plt.show()

def plot_scatter_plot(data, x_column, y_column, title=None, xlabel=None, ylabel=None, color='blue', save_path=None):
    plt.figure(figsize=(10, 6))
    plt.scatter(data[x_column], data[y_column], color=color)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if save_path:
        plt.savefig(save_path)
    plt.show()


def plot_heatmap(data, title=None, xlabel=None, ylabel=None, cmap='viridis', save_path=None):
    plt.figure(figsize=(10, 8))
    sns.heatmap(data.corr(), annot=True, fmt=".2f", cmap=cmap)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if save_path:
        plt.savefig(save_path)
    plt.show()


